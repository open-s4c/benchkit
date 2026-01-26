# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Compatibility bridge to keep legacy (old-engine) campaigns working while
benchmarks migrate to the new core protocol.

Why this module exists
----------------------
Benchkit is transitioning from the legacy campaign/benchmark stack to the new
core protocol:

- **Legacy stack**:
  - `benchkit.benchmark.Benchmark` (referred to as `BenchmarkOld` here) and
    `benchkit.campaign.CampaignCartesianProduct`.
  - Supports cartesian-product parameter exploration, CSV output, record
    directories, `continuing`, and legacy orchestration.
  - Provides extension points such as command wrappers, shared libraries
    (`LD_PRELOAD`), command attachments, and pre/post run hooks.

- **New core protocol**:
  - `benchkit.core.benchmark.Benchmark` protocol with the `fetch/build/run/collect` steps.
  - Executed by `benchkit.engine.stepper.Stepper`, which constructs typed contexts
    (`FetchContext`, `BuildContext`, `RunContext`, `CollectContext`) and stores
    step outputs in a `StepSession`.

For a transition period we want to:
- keep existing legacy campaigns (cartesian products, CSV layout, record dirs, etc.)
- run *new* protocol benchmarks without porting all legacy orchestration code at once.

This module provides that bridge by adapting a new-protocol benchmark to the legacy
`BenchmarkOld` interface expected by the old campaign engine.

How the bridge works
--------------------
The adapter is built around `Stepper`:

- `bootstrap()` executes `fetch()` once (legacy campaigns do not model fetch).
- `build_bench()` executes `build()` for each build-point.
- `single_run()` executes `run()` for each run-point / repetition.
- `parse_output_to_results()` executes `collect()` to produce record rows.

Legacy wrappers and shared libraries are applied by intercepting `RunContext.exec`:
`single_run()` uses the Stepper's `ctx_transform` hook (see `benchkit.engine.stepper`)
to replace the `exec` function inside `RunContext` with an adapter that:
1) computes `LD_PRELOAD` / env from `SharedLib` instances
2) applies `CommandWrapper` instances to argv/env
3) delegates to the original `ExecFn`

What works today
----------------
- Running new-protocol benchmarks through the legacy cartesian-product campaign engine.
- Record directories and results directory layout as produced by the legacy engine.
- `pre_run_hooks` and `post_run_hooks` (hook invocation remains owned by the legacy engine).
- `CommandWrapper` and `SharedLib` (`LD_PRELOAD`) support **provided the benchmark uses**
  `ctx.exec(...)` to run external commands.

Known limitations (important)
-----------------------------
- **CommandAttachment is not supported** (attachments often rely on async side processes).
- **Async execution is not supported**; this adapter returns synchronous stdout-like outputs.
- **Only commands executed through `ctx.exec` are wrappable**. If a benchmark uses
  `subprocess.*` directly (or otherwise bypasses `ctx.exec`), wrappers/sharedlibs
  cannot be injected by this compatibility layer.
- **Fetch arguments must be single-valued** in a legacy cartesian campaign. If a fetch
  parameter appears in `parameter_space`, it must have exactly one value because
  `fetch()` is executed once during `bootstrap()`.

API
---
The module exposes:

- :class:`Adapted`: a legacy `BenchmarkOld` implementation backed by a new core benchmark.
- :func:`CampaignCartesianProduct`: convenience helper returning a legacy campaign
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

import dataclasses
import inspect
import shlex
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from benchkit.benchmark import Benchmark as BenchmarkOld
from benchkit.benchmark import CommandAttachment, CommandWrapper, PostRunHook, PreRunHook, SharedLib
from benchkit.campaign import CampaignCartesianProduct as CampaignCartesianProductOld
from benchkit.core.benchmark import Benchmark
from benchkit.core.bktypes.contexts import RunContext
from benchkit.core.bktypes.execfn import ExecFn, ExecOutput
from benchkit.core.validatebench import validate_benchmark
from benchkit.engine.stepper import Stepper
from benchkit.platforms import Platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.dir import get_results_dir


def _get_params(step_fn: Callable) -> list[str]:
    """
    Return the parameter names of a step function, excluding the `ctx` parameter.

    This mirrors the argument discovery logic used by the Stepper (`_get_step_args`).

    Args:
        step_fn: A step function such as `bench.fetch`, `bench.build`, `bench.run`, etc.

    Returns:
        List of explicit parameter names excluding `ctx`.
    """
    sig = inspect.signature(step_fn)
    params = list(sig.parameters.keys())
    if "ctx" in params:
        params.remove("ctx")
    return params


def _check_fetch_args(
    benchmark: Benchmark,
    parameter_space: dict[str, Iterable[Any]],
) -> dict[str, Any]:
    """
    Extract and validate fetch arguments from a legacy cartesian parameter space.

    Legacy cartesian campaigns represent parameters as `{name -> values}`.
    Fetch is executed once during :meth:`Adapted.bootstrap`, so any fetch argument
    present in `parameter_space` must be single-valued.

    Args:
        benchmark: New-protocol benchmark instance.
        parameter_space: Legacy parameter space mapping.

    Returns:
        `{fetch_param_name -> single_value}` suitable for `Stepper.fetch(args=...)`.

    Raises:
        ValueError: if a fetch parameter is present and has a number of values != 1.
    """
    params = _get_params(step_fn=benchmark.fetch)
    fetch_args = {k: v for k, v in parameter_space.items() if k in params}

    for param_name, param_value in fetch_args.items():
        param_value_lst = list(param_value)
        # Legacy param spaces are expected to provide iterables of values.
        # For fetch args we enforce a single value.
        if 1 != len(param_value_lst):
            raise ValueError(
                "New->Old benchmark wrapper does not support multiple values "
                f"for fetch parameters: {param_name}: {param_value_lst}."
            )

    result = {k: list(v)[0] for k, v in fetch_args.items()}
    return result


def _make_legacy_exec(
    *,
    benchmark_old: BenchmarkOld,
    base_exec: ExecFn,
    variables: dict[str, Any],
) -> ExecFn:
    """
    Create an ExecFn wrapper that applies legacy wrappers/sharedlibs before delegating.

    This adapter is designed to be installed into `RunContext.exec` via
    `dataclasses.replace(run_ctx, exec=...)` in `Adapted.single_run()`.

    Args:
        benchmark_old: The legacy benchmark instance (provides `_preload_env`, `_wrap_command`).
        base_exec: The original ExecFn to delegate to (typically `run_ctx.exec`).
        variables: "Legacy variable dict" passed to wrappers/sharedlibs (build/run/other vars).

    Returns:
        An ExecFn compatible callable.
    """

    def legacy_exec(
        *,
        argv,
        cwd=None,
        env=None,
        timeout_s=None,
        record_dir=None,
        print_output=False,
        output_is_log=False,
        ignore_ret_codes=(),
        ignore_any_error_code=False,
    ) -> ExecOutput:
        # 0) Normalize argv into a list[str] for the legacy wrapper APIs.
        if isinstance(argv, str):
            run_command: list[str] = shlex.split(argv)
        else:
            run_command = list(argv)

        # 1) Build environment from SharedLibs (LD_PRELOAD etc.) and merge explicit env.
        #    Explicit env wins on conflicts.
        preload_env = benchmark_old._preload_env(**variables)  # pylint: disable=protected-access
        merged_env: dict[str, str] = {}
        if preload_env:
            merged_env.update(preload_env)
        if env:
            # Explicit env wins over preload_env
            merged_env.update(dict(env))

        # 2) Apply legacy CommandWrappers (may return env=None).
        wrapped_argv, wrapped_env = benchmark_old._wrap_command(  # pylint: disable=protected-access
            run_command=run_command,
            environment=merged_env or None,
            **variables,
        )

        # 3) Delegate to the original ExecFn.
        return base_exec(
            argv=wrapped_argv,
            cwd=cwd,
            env=wrapped_env or None,
            timeout_s=timeout_s,
            record_dir=record_dir,
            print_output=print_output,
            output_is_log=output_is_log,
            ignore_ret_codes=tuple(ignore_ret_codes),
            ignore_any_error_code=ignore_any_error_code,
        )

    return legacy_exec


class Adapted(BenchmarkOld):
    """
    Adapter implementing the legacy `BenchmarkOld` interface on top of a new-protocol benchmark.

    The legacy campaign engine calls:
      - `build_bench()` for each build-variable configuration
      - `single_run()` for each run-variable configuration (and repetition)
      - `parse_output_to_results()` to generate result records

    This adapter delegates those phases to a `Stepper`, which calls:
      - `fetch()` once during :meth:`bootstrap`
      - `build()` in :meth:`build_bench`
      - `run()` in :meth:`single_run`
      - `collect()` in :meth:`parse_output_to_results`

    Wrappers/sharedlibs are supported by injecting a wrapped ExecFn into `RunContext.exec`
    (only effective if the benchmark executes commands through `ctx.exec`).
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
            benchmark: New-protocol benchmark implementing fetch/build/run/collect.
            command_wrappers: Command wrappers (applied through `RunContext.exec`).
            command_attachments: Command attachments (not supported in this adapter).
            shared_libs: Shared libs (LD_PRELOAD injection; applied through `RunContext.exec`).
            pre_run_hooks: Pre-run hooks (executed by the legacy engine).
            post_run_hooks: Post-run hooks (executed by the legacy engine).
            platform: Optional platform override for the legacy benchmark.
        """
        if command_attachments:
            raise NotImplementedError(
                "Command attachments are not currently supported by this adapter."
            )

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
        args: dict[str, Iterable[Any]],
        record_dir: Path,
    ) -> None:
        """
        Execute the new benchmark's fetch step once and store its session.

        The legacy engine does not have a dedicated fetch phase. Therefore the adapter
        executes fetch once up-front using single-valued fetch arguments extracted
        from the provided legacy parameter space.

        Args:
            args: Legacy parameter space (may include many unrelated knobs).
            record_dir: Results directory used for the fetch step's record_dir.

        Raises:
            ValueError: If fetch arguments are provided with multiple values.
        """
        validate_benchmark(bench=self.benchmark)

        fetch_args = _check_fetch_args(benchmark=self.benchmark, parameter_space=args)
        self._session_fetch = self._stepper.fetch(args=fetch_args, record_dir=record_dir)

    @property
    def bench_src_path(self) -> Path:
        """
        Return the source directory of the fetched benchmark.

        Raises:
            ValueError: If the benchmark was not bootstrapped (fetch not executed).
        """
        if self._session_fetch is None:
            raise ValueError("Benchmark not bootstrapped.")
        return self._session_fetch.fetch_result.src_dir

    def get_build_var_names(self) -> List[str]:
        """
        Return build variable names as expected by the legacy engine.

        Derived from the new benchmark's `build()` signature.
        """
        return _get_params(step_fn=self.benchmark.build)

    def get_run_var_names(self) -> List[str]:
        """
        Return run variable names as expected by the legacy engine.

        Derived from the new benchmark's `run()` signature.
        """
        return _get_params(step_fn=self.benchmark.run)

    def build_bench(self, **kwargs) -> None:
        """
        Legacy build phase: call the new benchmark's build step through Stepper.

        Args:
            **kwargs: Build arguments (the legacy engine passes build vars here).
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

        Returns:
            Captured stdout of the run. This adapter currently returns a string and
            does not support legacy async execution.
        """
        run_args = dict(kwargs)
        duration_s = run_args.pop("benchmark_duration_seconds", None)

        def _transform_run_ctx(run_ctx: RunContext) -> RunContext:
            # Build the legacy "variables" mapping expected by wrappers/sharedlibs.
            other_variables = dict(run_ctx.fetch_args) | run_args.get("other_variables", {})
            variables = {
                "build_variables": dict(run_ctx.build_args),
                "run_variables": dict(run_ctx.run_args),
                "other_variables": other_variables,
                **dict(run_ctx.fetch_args),
                **dict(run_ctx.build_args),
                **dict(run_ctx.run_args),
                **dict(run_args.get("other_variables", {})),
            }

            legacy_exec = _make_legacy_exec(
                benchmark_old=self,
                base_exec=run_ctx.exec,
                variables=variables,
            )
            return dataclasses.replace(run_ctx, exec=legacy_exec)

        self._last_session_run = self._stepper.run(
            session=self._last_session_build,
            args=run_args,
            duration_s=duration_s,
            ctx_transform=_transform_run_ctx,
        )
        return self._last_session_run.run_result.outputs[-1].stdout

    def parse_output_to_results(self, **kwargs) -> Dict[str, Any]:
        """
        Legacy parse phase: call the new benchmark's collect step through Stepper.

        The legacy engine calls this with a mixture of arguments. We merge:
          - full kwargs (includes record_data_dir, etc.)
          - build_variables (if present)
          - run_variables (if present)

        This allows collect() implementations to receive what they need without forcing
        legacy code changes.

        Args:
            **kwargs: Legacy parse arguments.

        Returns:
            Record dictionary produced by the new benchmark's `collect()` step.
        """
        collect_args = kwargs | kwargs.get("build_variables", {}) | kwargs.get("run_variables", {})
        self._last_session_collect = self._stepper.collect(
            session=self._last_session_run,
            args=collect_args,
        )
        return self._last_session_collect.record_result


def CampaignCartesianProduct(
    name: str,
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
      3) Returns a legacy :class:`CampaignCartesianProductOld`.

    Args:
        benchmark: New protocol benchmark to run through the legacy engine.
        parameter_space: Legacy cartesian-product parameter space `{name -> values}`.
        nb_runs: Repetitions per cartesian point.
        duration_s: Legacy benchmark duration (seconds). Passed to the legacy engine as
            `benchmark_duration_seconds` and forwarded to the new run context as `duration_s`.
        results_dir: Optional base directory for results.
        command_wrappers: Legacy command wrappers (applied via `RunContext.exec` interception).
        command_attachments: Legacy command attachments (not supported).
        shared_libs: Legacy shared libs (applied via `RunContext.exec` interception).
        pre_run_hooks: Legacy pre-run hooks (supported; executed by legacy engine).
        post_run_hooks: Legacy post-run hooks (supported; executed by legacy engine).
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
        name=name,
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
