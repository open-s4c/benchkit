# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
benchkit benchmark protocol.

This module defines the core Benchmark protocol used by benchkit's refactored
execution model.

A benchmark in benchkit is a plain Python object that optionally exposes up to
four step methods:

- fetch(ctx, ...): obtain source code or inputs (optional)
- build(ctx, ...): compile or prepare artifacts (optional)
- run(ctx, ...): execute the workload and capture raw outputs (required)
- collect(ctx, ...): parse outputs and return measurement records (optional)

The engine orchestrates these steps by creating a context object for each step
(FetchContext, BuildContext, RunContext, CollectContext). Each context bundles:

- platform information and communication backend
- an exec() function to run commands
- variables shared across steps
- results of previous steps (e.g., fetch_result, build_result, run_result)
- step-specific argument dictionaries (fetch_args, build_args, run_args)

A key design choice is that benchmarks do not need to inherit from any base
class. Structural typing via typing.Protocol is used instead. This keeps
benchmark authoring lightweight and supports existing codebases with minimal
changes.

Each step must accept a "ctx" parameter that is compatible with keyword passing
(e.g., ctx=...). The convenience methods like ctx.call(...) rely on this.

Note:
- Only run() is required for a valid benchmark. If fetch/build/collect are not
  present, the engine can skip those stages (or provide default behavior).
- The exact additional parameters of each step are benchmark-specific. They are
  represented using a ParamSpec so type checkers can propagate argument shapes
  when possible.
"""

from typing import ParamSpec, Protocol

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext

# P represents the variable "Parameter Specification" (the arguments) for step methods.
P = ParamSpec("P")


class Benchmark(Protocol[P]):
    """
    Protocol describing the expected shape of a benchkit benchmark.

    Implementations may define any subset of the methods below, but run() is
    required by the engine.

    The method signatures allow arbitrary *args/**kwargs so that benchmarks can
    expose any parameters they need (e.g., commit, dataset path, thread count).
    When using ctx.call(...), contexts may filter which keyword arguments are
    forwarded based on the target function signature.
    """

    def fetch(
        self,
        ctx: FetchContext,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> FetchResult:
        """
        Fetch inputs needed by the benchmark.

        Typical responsibilities:
        - clone a git repository
        - download datasets
        - apply patches
        - return the source directory and related metadata

        This step is optional.

        Args:
            ctx: FetchContext providing platform and exec() capabilities.
            *args: Benchmark-specific positional arguments (discouraged; prefer kwargs).
            **kwargs: Benchmark-specific keyword arguments, usually coming from
                FetchContext.fetch_args.

        Returns:
            FetchResult describing where the sources/inputs were obtained.
        """
        ...

    def build(
        self,
        ctx: BuildContext,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> BuildResult:
        """
        Build or prepare artifacts needed to execute the workload.

        Typical responsibilities:
        - compile binaries
        - generate intermediate files
        - prepare a working database or cache

        This step is optional.

        Args:
            ctx: BuildContext providing access to fetch_result plus exec() capabilities.
            *args: Benchmark-specific positional arguments (discouraged; prefer kwargs).
            **kwargs: Benchmark-specific keyword arguments, usually coming from
                BuildContext.build_args.

        Returns:
            BuildResult describing build directories and additional artifacts.
        """
        ...

    def run(
        self,
        ctx: RunContext,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> RunResult:
        """
        Execute the workload.

        This is the only required step. It should run the benchmarked program(s)
        and capture enough raw output for later parsing (stdout/stderr, files,
        logs, etc.). The engine will provide run-time parameters via run_args.

        Args:
            ctx: RunContext providing access to fetch_result/build_result plus exec().
            *args: Benchmark-specific positional arguments (discouraged; prefer kwargs).
            **kwargs: Benchmark-specific keyword arguments, usually coming from
                RunContext.run_args.

        Returns:
            RunResult containing one or more ExecOutput objects and any runtime artifacts.
        """
        ...

    def collect(
        self,
        ctx: CollectContext,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> RecordResult:
        """
        Collect and return measurement records.

        This step parses raw outputs produced by run() and returns record rows
        to be appended to a CSV (or stored in another backend).

        This step is optional. If omitted, an engine may still persist raw outputs
        but no structured records will be produced.

        Args:
            ctx: CollectContext providing access to fetch_result/build_result/run_result.
            *args: Benchmark-specific positional arguments (discouraged; prefer kwargs).
            **kwargs: Benchmark-specific keyword arguments. CollectContext.call()
                may forward a subset of (fetch_args | build_args | run_args) based
                on this method's signature.

        Returns:
            RecordResult: either one dict (single record) or a list of dicts
            (multi-line results).
        """
        ...
