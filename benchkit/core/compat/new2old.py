# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Compatibility bridge to keep legacy (old-engine) campaigns working while
benchmarks migrate to the new core protocol.

Why this module exists
----------------------
Benchkit currently has two "layers" that are being transitioned:

- **Old engine** (legacy):
  - `benchkit.benchmark.Benchmark` and `benchkit.campaign.CampaignCartesianProduct`
  - Supports cartesian-product parameter exploration, CSV output, record directories,
    `continuing`, and legacy orchestration.
  - Provides extension points such as command wrappers, attachments, shared libraries
    and pre/post run hooks.

- **New core protocol**:
  - `benchkit.core.benchmark.Benchmark` with the `fetch/build/run/collect` steps.
  - Executed via `benchkit.engine.Stepper`, which constructs typed contexts and
    captures step outputs in `StepSession`.

For a transition period we want to:
- keep existing legacy campaigns (cartesian products, CSV layout, record dirs, etc.)
- run *new* protocol benchmarks without porting all old orchestration code at once.

This module provides that bridge by adapting a new-protocol benchmark to the legacy
`Benchmark` interface expected by the old campaign engine.

What works today
----------------
- Running new protocol benches through the legacy cartesian-product campaign engine.
- Record directories and results directory handling (via the legacy engine).
- Legacy `pre_run_hooks` and `post_run_hooks` (validated by tests).
- Reuse of the new `Stepper` to call `fetch/build/run/collect` with signature-based
  argument filtering.

Known limitations (important)
-----------------------------
This adapter does **not yet** preserve legacy features that mutate the command line
or environment of the executed workload:

- `CommandWrapper` (e.g., taskset/numactl/perf wrappers)
- `SharedLib` / `LD_PRELOAD` injection
- `CommandAttachment` (async side processes)

In the legacy engine, those features are applied in `BenchmarkOld.run_bench_command()`
and related helpers. The new core protocol executes through `ctx.exec()` (via Stepper)
and currently bypasses that legacy wrapping machinery.

This module intentionally keeps the implementation minimal for now; the next step is
to route execution through an "exec adapter" that applies wrappers/sharedlibs/
attachments before dispatching the command.

API
---
The module exposes:

- :class:`Adapted`: a legacy `BenchmarkOld` implementation backed by a new core benchmark.
- :func:`CampaignCartesianProduct`: convenience function returning a legacy campaign
  configured with an adapted benchmark.

The convenience function is primarily meant for existing "kit" style campaign scripts
that expect the old `CampaignCartesianProduct` API.

Example
-------
    >>> from benchkit.benches.leveldb import LevelDBBench
    >>> from benchkit.core.compat.new2old import CampaignCartesianProduct
    >>>
    >>> parameter_space = {
    ...     "bench_name": ["readrandom", "seekrandom"],
    ...     "nb_threads": [2, 4, 8],
    ... }
    >>> campaign = CampaignCartesianProduct(
    ...     benchmark=LevelDBBench(),
    ...     parameter_space=parameter_space,
    ...     nb_runs=1,
    ...     duration_s=5,
    ... )
    >>> campaign.run()

Notes on fetch arguments
-----------------------
The new protocol supports a dedicated `fetch()` step which may accept arguments
such as `parent_dir`, `commit`, `patches`, etc. In a legacy cartesian campaign we
expect fetch parameters to be fixed (single-valued). Therefore this adapter enforces:

- If a fetch parameter appears in the provided `parameter_space`, it must have exactly
  one value.

If you want to vary fetch parameters, use the new engine directly rather than the
legacy cartesian-product runner.

"""

import inspect
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from benchkit.benchmark import Benchmark as BenchmarkOld
from benchkit.benchmark import CommandAttachment, CommandWrapper, PostRunHook, PreRunHook, SharedLib
from benchkit.campaign import CampaignCartesianProduct as CampaignCartesianProductOld
from benchkit.core.benchmark import Benchmark
from benchkit.engine.stepper import Stepper
from benchkit.platforms import Platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.dir import get_results_dir


def _get_params(step_fn: Callable) -> list[str]:
    """
    Return the parameter names of a step function, excluding the context parameter.

    This mirrors the argument discovery logic used by the Stepper (`_get_step_args`).

    Args:
        step_fn: A step function such as `bench.fetch`, `bench.build`, `bench.run`, etc.

    Returns:
        The list of explicit argument names (excluding the `ctx` parameter).
    """
    sig = inspect.signature(step_fn)
    params = list(sig.parameters.keys())
    if "ctx" in params:
        params.remove("ctx")
    return params


def _check_fetch_args(
    benchmark: Benchmark,
    parameter_space: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract and validate fetch arguments from a legacy cartesian parameter space.

    The legacy cartesian campaign passes a parameter space as a mapping
    `{name -> iterable(values)}`. Fetch arguments must be single-valued in that
    representation, because fetch is executed once during adapter bootstrap.

    Args:
        benchmark: New protocol benchmark.
        parameter_space: Legacy-style parameter space mapping.

    Returns:
        A dictionary `{fetch_param_name -> single_value}` suitable to call `fetch()`.

    Raises:
        ValueError: if a fetch parameter is present and has a number of values != 1.
    """
    params = _get_params(step_fn=benchmark.fetch)
    fetch_args = {k: v for k, v in parameter_space.items() if k in params}

    for param_name, param_value in fetch_args.items():
        # Legacy param spaces are expected to provide iterables of values.
        # For fetch args we enforce a single value.
        if 1 != len(param_value):
            raise ValueError(
                "New->Old benchmark wrapper does not support multiple values "
                f"for fetch parameters: {param_name}: {param_value}."
            )

    return {k: v[0] for k, v in fetch_args.items()}


class Adapted(BenchmarkOld):
    """
    Adapter implementing the legacy `BenchmarkOld` interface on top of a new-protocol benchmark.

    The legacy campaign engine calls into:
      - `build_bench()` for each build-variable configuration
      - `single_run()` for each run-variable configuration (and repetition)
      - `parse_output_to_results()` to generate result records

    This adapter delegates those phases to a `Stepper`, which calls:
      - `fetch()` once during :meth:`bootstrap`
      - `build()` in :meth:`build_bench`
      - `run()` in :meth:`single_run`
      - `collect()` in :meth:`parse_output_to_results`

    Important:
        This adapter currently **does not** apply legacy wrappers/sharedlibs/attachments.
        Hooks work because the legacy engine owns the hook invocation logic around
        `single_run()` and `parse_output_to_results()`.
    """

    def __init__(
        self,
        benchmark: Benchmark,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform | None = None,
    ) -> None:
        """
        Create an adapted benchmark.

        Args:
            benchmark: New protocol benchmark implementing fetch/build/run/collect.
            command_wrappers: Legacy command wrappers (currently ignored by the adapter
                execution path; accepted to keep legacy campaign scripts unchanged).
            command_attachments: Legacy command attachments (currently ignored).
            shared_libs: Legacy shared libs (currently ignored).
            pre_run_hooks: Legacy pre-run hooks (supported by old engine).
            post_run_hooks: Legacy post-run hooks (supported by old engine).
            platform: Optional platform override for the legacy benchmark.
        """
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform

        self.benchmark = benchmark
        self._stepper = Stepper(bench=self.benchmark, platform=self.platform)

        # Sessions are created by Stepper and consumed across steps.
        self._session_fetch = None
        self._last_session_build = None
        self._last_session_run = None
        self._last_session_collect = None

    def bootstrap(
        self,
        args: dict[str, Any],
        record_dir: Path,
    ) -> None:
        """
        Execute the new benchmark's fetch step once and store its session.

        The legacy engine does not have a dedicated fetch phase; therefore the adapter
        performs fetch once up-front using single-valued fetch arguments extracted
        from the provided legacy parameter space.

        Args:
            args: Legacy parameter space (may include many unrelated knobs).
            record_dir: Results directory used for the fetch step's record_dir.

        Raises:
            ValueError: If fetch arguments are provided with multiple values.
        """
        fetch_args = _check_fetch_args(benchmark=self.benchmark, parameter_space=args)
        self._session_fetch = self._stepper.fetch(args=fetch_args, record_dir=record_dir)

    @property
    def bench_src_path(self) -> Path:
        """
        Return the source directory of the fetched benchmark.

        The legacy engine uses this for metadata (git SHA, branch, etc.). We map it
        to the new fetch result's `src_dir`.

        Raises:
            ValueError: If the benchmark was not bootstrapped (fetch not executed).
        """
        if self._session_fetch is None:
            raise ValueError("Benchmark not bootstrapped.")
        return self._session_fetch.fetch_result.src_dir

    def get_build_var_names(self) -> List[str]:
        """
        Return build variable names as expected by the legacy engine.

        This is derived from the new benchmark's `build()` signature.
        """
        return _get_params(step_fn=self.benchmark.build)

    def get_run_var_names(self) -> List[str]:
        """
        Return run variable names as expected by the legacy engine.

        This is derived from the new benchmark's `run()` signature.
        """
        return _get_params(step_fn=self.benchmark.run)

    def build_bench(self, **kwargs) -> None:
        """
        Legacy build phase: call the new benchmark's build step through Stepper.

        Args:
            **kwargs: Build arguments (the legacy engine only passes build vars here).
        """
        self._last_session_build = self._stepper.build(
            session=self._session_fetch,
            args=kwargs,
        )

    def single_run(self, **kwargs) -> str | AsyncProcess:
        """
        Legacy run phase: call the new benchmark's run step through Stepper.

        The legacy engine passes `benchmark_duration_seconds`, which is translated to
        `duration_s` expected by Stepper/RunContext.

        Args:
            **kwargs: Run arguments and legacy orchestration parameters.

        Returns:
            The captured stdout of the run. The adapter always returns a string for now.
            (Legacy async mode via attachments is not supported yet.)
        """
        run_args = dict(kwargs)
        duration_s = run_args.pop("benchmark_duration_seconds", None)

        self._last_session_run = self._stepper.run(
            session=self._last_session_build,
            args=run_args,
            duration_s=duration_s,
        )
        return self._last_session_run.run_result.outputs[-1].stdout

    def parse_output_to_results(self, **kwargs) -> Dict[str, Any]:
        """
        Legacy parse phase: call the new benchmark's collect step through Stepper.

        The legacy engine calls this with a mixture of arguments. We merge:
          - the full kwargs (includes record_data_dir, etc.)
          - build_variables (if present)
          - run_variables (if present)

        This allows collect() implementations to receive what they need without forcing
        legacy code changes.

        Args:
            **kwargs: Legacy parse arguments.

        Returns:
            The record dictionary produced by the new benchmark's `collect()` step.
        """
        collect_args = kwargs | kwargs.get("build_variables", {}) | kwargs.get("run_variables", {})
        self._last_session_collect = self._stepper.collect(
            session=self._last_session_run,
            args=collect_args,
        )
        return self._last_session_collect.record_result


def CampaignCartesianProduct(
    benchmark: Benchmark,
    parameter_space: dict[str, Iterable[Any]],
    nb_runs: int = 1,
    duration_s: int = 5,
    results_dir: Path | None = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
) -> CampaignCartesianProductOld:
    """
    Create a legacy cartesian-product campaign for a new-protocol benchmark.

    This helper:
      1) Creates an :class:`Adapted` benchmark.
      2) Executes fetch once (bootstrap).
      3) Builds and returns a legacy :class:`CampaignCartesianProductOld`.

    Args:
        benchmark: New protocol benchmark to run through the legacy engine.
        parameter_space: Legacy cartesian-product parameter space `{name -> values}`.
        nb_runs: Repetitions per cartesian point.
        duration_s: Legacy benchmark duration (seconds). Passed to legacy engine as
            `benchmark_duration_seconds` and forwarded to the new run context as `duration_s`.
        results_dir: Optional base directory for results.
        command_wrappers: Legacy command wrappers (currently not applied by adapter execution).
        command_attachments: Legacy command attachments (currently not applied).
        shared_libs: Legacy shared libs (currently not applied).
        pre_run_hooks: Legacy pre-run hooks (supported).
        post_run_hooks: Legacy post-run hooks (supported).
        platform: Optional platform override.

    Returns:
        A legacy campaign object ready to run.

    Raises:
        ValueError: If fetch arguments are provided with multiple values.
    """
    results_dir = get_results_dir(results_dir=results_dir)

    benchmark_old = Adapted(
        benchmark=benchmark,
        command_wrappers=command_wrappers,
        command_attachments=command_attachments,
        shared_libs=shared_libs,
        pre_run_hooks=pre_run_hooks,
        post_run_hooks=post_run_hooks,
        platform=platform,
    )
    benchmark_old.bootstrap(
        args=parameter_space,
        record_dir=results_dir,
    )

    return CampaignCartesianProductOld(
        name="campaign",
        benchmark=benchmark_old,
        nb_runs=nb_runs,
        variables=parameter_space,
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=duration_s,
        results_dir=results_dir,
        pretty=None,
        filter_func=None,
        symlink_latest=False,
    )
