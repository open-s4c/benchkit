# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Step binding and execution utilities.

This module is responsible for:
- selecting the right subset of Vars for each benchmark step by introspecting
  the step signature
- validating required parameters are provided (when missing, raise clear errors)
- building step contexts (FetchContext, BuildContext, RunContext, CollectContext)
- executing steps through an Executor TODO not yet

This logic is reused by engines to avoid duplication.

Separation of concerns:
- Executor: mechanics (run a callable, possibly with parallelism/remoting later)
- Engine: orchestration (how many times, what record policy, cartesian products)
- Stepper: binding + context construction + step-level validation + execution
"""

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from benchkit.core.benchmark import Benchmark
from benchkit.core.bktypes import RecordResult, Vars
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.platforms import Platform


class MissingStepArgError(ValueError):
    """
    Raised when a required step argument is missing from the provided args.
    """


@dataclass(frozen=True)
class StepSession:
    """
    Captures contexts and results as we progress through the pipeline.

    Engines can reuse this object to build more complex orchestration without
    replicating step binding logic.
    """

    fetch_ctx: FetchContext
    fetch_result: FetchResult | None = None

    build_ctx: BuildContext | None = None
    build_result: BuildResult | None = None

    run_ctx: RunContext | None = None
    run_result: RunResult | None = None

    collect_ctx: CollectContext | None = None
    record_result: RecordResult | None = None


def _get_step_args(
    step_fn: Callable,
    step_name: str,
    args: Vars,
) -> tuple[Vars, Vars]:
    sig = inspect.signature(step_fn)
    sig_params = sig.parameters
    params = list(sig_params.keys())
    if "ctx" in params:
        params.remove("ctx")

    # Missing args in provided args:
    missing_args = [k for k in params if k not in args]

    # Check if the missing args have default values:
    defaulted_args = {
        a: p.default
        for a in missing_args
        if (p := sig_params[a]).default is not inspect.Parameter.empty
    }

    # Filter out parameters with default values:
    missing_args = [a for a in missing_args if a not in defaulted_args]

    if missing_args:
        provided = ""
        if args:
            provided = ", ".join(f'{k} ("{v}")' for k, v in args.items())
            provided = f"Provided: {provided}."
        raise MissingStepArgError(
            f"Missing required arguments in {step_name}(): {', '.join(missing_args)}.{provided}"
        )

    step_args = {k: args[k] for k in params if k in args}
    return step_args, defaulted_args


@dataclass(frozen=True)
class Stepper:
    bench: Benchmark
    platform: Platform

    def fetch(
        self,
        args: Vars,
        record_dir: Path | None = None,
    ) -> StepSession:
        do_fetch = hasattr(self.bench, "fetch")
        fetch_args = {}
        default_args = {}
        fetch_result = None

        if do_fetch:
            fetch_args, default_args = _get_step_args(
                step_fn=self.bench.fetch,
                step_name="fetch",
                args=args,
            )

        fetch_context = FetchContext.from_args(
            fetch_args=fetch_args,
            vars=args,
            default_args=default_args,
            platform=self.platform,
            record_dir=record_dir,
        )
        if do_fetch:
            fetch_result = fetch_context.call(self.bench.fetch)

        result = StepSession(fetch_ctx=fetch_context, fetch_result=fetch_result)
        return result

    def build(self, session: StepSession, args: Vars) -> StepSession:
        do_build = hasattr(self.bench, "build")
        build_args = {}
        default_args = {}
        build_result = None

        if do_build:
            build_args, default_args = _get_step_args(
                step_fn=self.bench.build,
                step_name="build",
                args=args,
            )

        build_ctx = BuildContext.from_fetch(
            ctx=session.fetch_ctx,
            fetch_result=session.fetch_result,
            build_args=build_args,
            default_args=default_args,
        )

        if do_build:
            build_result = build_ctx.call(self.bench.build)

        result = StepSession(
            fetch_ctx=session.fetch_ctx,
            fetch_result=session.fetch_result,
            build_ctx=build_ctx,
            build_result=build_result,
        )
        return result

    def run(self, session: StepSession, args: Vars, duration_s: int | None) -> StepSession:
        run_args, default_args = _get_step_args(step_fn=self.bench.run, step_name="run", args=args)
        run_ctx = RunContext.from_build(
            ctx=session.build_ctx,
            build_result=session.build_result,
            run_args=run_args,
            default_args=default_args,
            duration_s=duration_s,
        )
        run_result = run_ctx.call(self.bench.run)
        result = StepSession(
            fetch_ctx=session.fetch_ctx,
            fetch_result=session.fetch_result,
            build_ctx=session.build_ctx,
            build_result=session.build_result,
            run_ctx=run_ctx,
            run_result=run_result,
        )
        return result

    def collect(self, session: StepSession, args: Vars) -> StepSession:
        do_collect = hasattr(self.bench, "collect")
        collect_result = {}
        collect_args = {}
        default_args = {}

        if do_collect:
            collect_args, default_args = _get_step_args(
                step_fn=self.bench.collect,
                step_name="collect",
                args=args,
            )

        collect_ctx = CollectContext.from_run(
            ctx=session.run_ctx,
            run_result=session.run_result,
            default_args=default_args,
        )

        if do_collect:
            collect_result = self.bench.collect(ctx=collect_ctx, **collect_args)

        result = StepSession(
            fetch_ctx=session.fetch_ctx,
            fetch_result=session.fetch_result,
            build_ctx=session.build_ctx,
            build_result=session.build_result,
            run_ctx=session.run_ctx,
            run_result=session.run_result,
            collect_ctx=collect_ctx,
            record_result=collect_result,
        )
        return result
