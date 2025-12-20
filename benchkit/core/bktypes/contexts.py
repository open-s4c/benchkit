# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Context objects for benchmark execution phases.

This module defines context objects passed to each benchmark phase:
- FetchContext: Context for source code fetching
- BuildContext: Context for building the benchmark
- RunContext: Context for running the benchmark
- CollectContext: Context for collecting measurements

Each context provides:
- Platform information (OS, architecture, communication interface)
- Execution function for running commands
- Variables and results from previous phases
- A call() method to invoke benchmark methods with automatic argument filtering
"""

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from benchkit.core.bktypes import RecordResult, Vars
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.execfn import ExecFn, shell2exec
from benchkit.platforms import Platform, get_current_platform


@dataclass(frozen=True, kw_only=True)
class BaseContext:
    """
    Base context containing shared fields for all benchmark phases.

    Attributes:
        platform: Platform information (OS, architecture, communication interface).
        exec: Function for executing commands synchronously.
        vars: Dictionary of arbitrary benchmark variables shared across phases.
        record_dir: Optional directory for storing execution artifacts and logs.
    """

    platform: Platform = get_current_platform()
    exec: ExecFn = shell2exec(platform.comm.shell)
    vars: Vars = field(default_factory=dict)
    record_dir: Path | None = None


@dataclass(frozen=True, kw_only=True)
class FetchContext(BaseContext):
    """
    Context for the fetch phase.

    Provides access to fetch-specific arguments and platform capabilities.

    Attributes:
        fetch_args: Dictionary of arguments specific to the fetch operation
                   (e.g., repository URL, commit hash, parent directory).
    """

    fetch_args: Vars

    @classmethod
    def from_args(
        cls,
        fetch_args: Vars,
        vars: Vars | None = None,
        platform: Platform | None = None,
        exec_fn: ExecFn | None = None,
        record_dir: Path | None = None,
    ) -> "FetchContext":
        """
        Create a FetchContext from fetch arguments.

        Args:
            fetch_args: Fetch-specific arguments (e.g., url, commit, parent_dir).
            vars: Optional initial benchmark variables (defaults to copy of fetch_args).
            platform: Optional platform override (defaults to current platform).
            exec_fn: Optional execution function override.
            record_dir: Optional directory for storing artifacts.

        Returns:
            A FetchContext instance ready for use.
        """
        platform = platform or get_current_platform()
        exec_fn = exec_fn or shell2exec(platform.comm.shell)
        return cls(
            platform=platform,
            exec=exec_fn,
            vars=vars or dict(fetch_args),
            record_dir=record_dir,
            fetch_args=fetch_args,
        )

    def call(self, fn: Callable) -> FetchResult:
        """
        Invoke a fetch function with this context.

        Automatically passes ctx=self and unpacks fetch_args as keyword arguments.

        Args:
            fn: The fetch function to call (e.g., benchmark.fetch).

        Returns:
            FetchResult from the function.
        """
        return fn(ctx=self, **self.fetch_args)


@dataclass(frozen=True, kw_only=True)
class BuildContext(BaseContext):
    """
    Context for the build phase.

    Inherits platform capabilities and adds fetch results and build arguments.

    Attributes:
        fetch_args: Arguments used during the fetch phase.
        fetch_result: Result from the fetch phase (source code location).
        build_args: Dictionary of build-specific arguments (e.g., compiler flags, targets).
    """

    fetch_args: Vars
    fetch_result: FetchResult
    build_args: Vars

    @classmethod
    def from_fetch(
        cls,
        ctx: FetchContext,
        fetch_result: FetchResult,
        build_args: Vars,
    ) -> "BuildContext":
        """
        Create a BuildContext from a completed fetch phase.

        Args:
            ctx: The FetchContext from the previous phase.
            fetch_result: The result returned by the fetch phase.
            build_args: Build-specific arguments (e.g., compiler, optimization level).

        Returns:
            A BuildContext instance ready for building.
        """
        return cls(
            platform=ctx.platform,
            exec=ctx.exec,
            vars=ctx.vars,
            record_dir=ctx.record_dir,
            fetch_args=ctx.fetch_args,
            fetch_result=fetch_result,
            build_args=build_args,
        )

    def call(self, fn: Callable) -> BuildResult:
        """
        Invoke a build function with this context.

        Automatically passes ctx=self and unpacks build_args as keyword arguments.

        Args:
            fn: The build function to call (e.g., benchmark.build).

        Returns:
            BuildResult from the function.
        """
        return fn(ctx=self, **self.build_args)


@dataclass(frozen=True, kw_only=True)
class RunContext(BaseContext):
    """
    Context for the run phase.

    Contains all previous phase results and run-specific parameters.

    Attributes:
        fetch_args: Arguments used during the fetch phase.
        fetch_result: Result from the fetch phase.
        build_args: Arguments used during the build phase.
        build_result: Result from the build phase (build artifacts, paths).
        run_args: Dictionary of run-specific arguments (e.g., workload, threads).
        duration_s: Optional duration limit for the benchmark run in seconds.
    """

    fetch_args: Vars
    fetch_result: FetchResult
    build_args: Vars
    build_result: BuildResult
    run_args: Vars
    duration_s: int | None = None

    @classmethod
    def from_build(
        cls,
        ctx: BuildContext,
        build_result: BuildResult,
        run_args: Vars,
        duration_s: int | None = None,
    ) -> "RunContext":
        """
        Create a RunContext from a completed build phase.

        Args:
            ctx: The BuildContext from the previous phase.
            build_result: The result returned by the build phase.
            run_args: Run-specific arguments (e.g., benchmark name, thread count).
            duration_s: Optional duration limit in seconds.

        Returns:
            A RunContext instance ready for execution.
        """
        return cls(
            platform=ctx.platform,
            exec=ctx.exec,
            vars=ctx.vars,
            record_dir=ctx.record_dir,
            fetch_args=ctx.fetch_args,
            fetch_result=ctx.fetch_result,
            build_args=ctx.build_args,
            build_result=build_result,
            run_args=run_args,
            duration_s=duration_s,
        )

    def call(self, fn: Callable) -> RunResult:
        """
        Invoke a run function with this context.

        Automatically passes ctx=self and unpacks run_args as keyword arguments.

        Args:
            fn: The run function to call (e.g., benchmark.run).

        Returns:
            RunResult from the function.
        """
        return fn(ctx=self, **self.run_args)


@dataclass(frozen=True, kw_only=True)
class CollectContext(BaseContext):
    """
    Context for the collect phase.

    Contains results from all previous phases for parsing and measurement collection.

    Attributes:
        fetch_args: Arguments used during the fetch phase.
        fetch_result: Result from the fetch phase.
        build_args: Arguments used during the build phase.
        build_result: Result from the build phase.
        run_args: Arguments used during the run phase.
        run_result: Result from the run phase (command outputs, artifacts).
    """

    fetch_args: Vars
    fetch_result: FetchResult
    build_args: Vars
    build_result: BuildResult
    run_args: Vars
    run_result: RunResult

    @classmethod
    def from_run(
        cls,
        ctx: RunContext,
        run_result: RunResult,
    ) -> "CollectContext":
        """
        Create a CollectContext from a completed run phase.

        Args:
            ctx: The RunContext from the previous phase.
            run_result: The result returned by the run phase.

        Returns:
            A CollectContext instance ready for measurement collection.
        """
        return cls(
            platform=ctx.platform,
            exec=ctx.exec,
            vars=ctx.vars,
            record_dir=ctx.record_dir,
            fetch_args=ctx.fetch_args,
            fetch_result=ctx.fetch_result,
            build_args=ctx.build_args,
            build_result=ctx.build_result,
            run_args=ctx.run_args,
            run_result=run_result,
        )

    def call(self, fn: Callable) -> RecordResult:
        """
        Invoke a collect function with this context.

        Automatically passes ctx=self and filters arguments from all phases based on
        the function's signature. Only arguments that the function accepts are passed.

        Args:
            fn: The collect function to call (e.g., benchmark.collect).

        Returns:
            RecordResult (dict or list of dicts) containing measurements.
        """
        fn_params = list(inspect.signature(fn).parameters)
        fn_params.remove("ctx")

        args = self.fetch_args | self.build_args | self.run_args
        real_args = {k: v for k, v in args.items() if k in fn_params}

        return fn(ctx=self, **real_args)
