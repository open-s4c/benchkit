# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Will-it-scale benchmark implementation for benchkit.

This module implements the benchkit protocol for the Will-it-scale
microbenchmark suite. Will-it-scale is a collection of kernel-level
scalability benchmarks commonly used to evaluate lock and synchronization
behavior under increasing thread counts.

The implementation covers:
- Fetching the Will-it-scale source code from GitHub (optionally applying patches)
- Building a selected benchmark test target
- Running the test with a configurable number of threads and duration
- Parsing aggregated operation counts from the benchmark output

Example:
    >>> from pathlib import Path
    >>> bench = WillitscaleBench()

    # ------------------------------------------------------------------
    # Fetch: clone Will-it-scale sources (and apply optional patches)
    # ------------------------------------------------------------------
    >>> fetch_ctx = FetchContext.from_args(
    ...     fetch_args={
    ...         "parent_dir": Path("/tmp/src"),
    ...         "commit": "master",
    ...         "patches": [Path("/tmp/patches/patch.diff")],
    ...     }
    ... )
    >>> fetch_result = bench.fetch(ctx=fetch_ctx, **fetch_ctx.fetch_args)

    # ------------------------------------------------------------------
    # Build: compile a Will-it-scale test
    # ------------------------------------------------------------------
    >>> build_ctx = BuildContext.from_fetch(
    ...     fetch_ctx=fetch_ctx,
    ...     fetch_result=fetch_result,
    ... )
    >>> build_result = bench.build(
    ...     ctx=build_ctx,
    ...     test_name="lock1_processes",
    ...     nb_warmup_iterations=1,
    ... )

    # ------------------------------------------------------------------
    # Run: execute the benchmark
    # ------------------------------------------------------------------
    >>> run_ctx = RunContext.from_build(
    ...     build_ctx=build_ctx,
    ...     build_result=build_result,
    ...     duration_s=1.0,
    ... )
    >>> run_result = bench.run(
    ...     ctx=run_ctx,
    ...     test_name="lock1_processes",
    ...     nb_threads=4,
    ... )

    # ------------------------------------------------------------------
    # Collect: parse performance metrics
    # ------------------------------------------------------------------
    >>> collect_ctx = CollectContext.from_run(
    ...     run_ctx=run_ctx,
    ...     run_result=run_result,
    ... )
    >>> record = bench.collect(ctx=collect_ctx)
    >>> record["global_count"]
"""


import re
from pathlib import Path

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.buildtools import build_dir_from_ctx, make
from benchkit.utils.fetchtools import git_clone


class WillitscaleBench:
    """
    Benchmark implementation for the Will-it-scale microbenchmark suite.

    This class implements all phases of the benchkit protocol:
    - fetch: Clone the Will-it-scale repository from GitHub
    - build: Compile a selected Will-it-scale test target
    - run: Execute the test with a configurable thread count and duration
    - collect: Parse aggregated operation counts from the benchmark output
    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Path,
        commit: str = "",
    ) -> FetchResult:
        """
        Fetch the Will-it-scale benchmark source code.

        Clones the Will-it-scale Git repository and checks out the specified
        commit, tag, or branch. If no commit is specified, the default branch
        is used.

        Args:
            ctx: FetchContext providing platform and execution capabilities.
            parent_dir: Directory where the Will-it-scale repository will be cloned.
            commit: Git commit hash, tag, or branch name.
                An empty string means the default branch is used.

        Returns:
            FetchResult containing the path to the cloned repository.

        Example:
            >>> fetch_result = bench.fetch(
            ...     ctx=fetch_ctx,
            ...     parent_dir=Path("/tmp/src"),
            ...     commit="master",
            ... )
        """

        willitscale_dir = git_clone(
            ctx=ctx,
            url="https://github.com/antonblanchard/will-it-scale.git",
            commit=commit,
            parent_dir=parent_dir,
        )

        return FetchResult(src_dir=willitscale_dir)

    def build(
        self,
        ctx: BuildContext,
        test_name: str,
        nb_warmup_iterations: int,
    ) -> BuildResult:
        """
        Build a Will-it-scale benchmark test.

        Cleans previous build artifacts and compiles the requested test target,
        using an out-of-tree object directory and the configured warmup iteration
        count.

        Args:
            ctx: BuildContext providing fetch results and execution capabilities.
            test_name: Name of the Will-it-scale test target to build (e.g., "lock1_processes").
            nb_warmup_iterations: Number of warmup iterations compiled into the test.

        Returns:
            BuildResult containing:
                - build_dir: Path to the source directory used for the build.

        Example:
            >>> build_result = bench.build(
            ...     ctx=build_ctx,
            ...     test_name="lock1_processes",
            ...     nb_warmup_iterations=1,
            ... )
        """

        src_dir = ctx.fetch_result.src_dir
        obj_dir = build_dir_from_ctx(ctx=ctx)

        make(
            ctx=ctx,
            src_dir=src_dir,
            targets=["clean"],
            options={},
        )

        make(
            ctx=ctx,
            src_dir=src_dir,
            targets=[test_name],
            options={"OBJ_DIR": f"{obj_dir}", "WARMUP_ITERATIONS": str(nb_warmup_iterations)},
        )

        result = BuildResult(
            build_dir=src_dir,
            other={},
        )
        return result

    def run(
        self,
        ctx: RunContext,
        test_name: str,
        nb_threads: int = 2,
    ) -> RunResult:
        """
        Execute a will it scale benchmark test.

        Runs the specified test with a given number of threads and duration.
        The duration is taken from ctx.duration_s.

        Args:
            ctx: RunContext providing execution capabilities and build results.
            test_name: Name of the test binary to execute.
            nb_threads: Number of threads to use (default: 2).

        Returns:
            RunResult containing the execution output of the test.

        Example:
            >>> run_result = bench.run(
            ...     ctx=run_ctx,
            ...     test_name="lock1_processes",
            ...     nb_threads=4,
            ... )
        """

        duration_s = ctx.duration_s
        build_dir = ctx.build_result.build_dir

        run_command = [
            f"./{test_name}",
            "-t",
            f"{nb_threads}",
            "-s",
            f"{duration_s}",
        ]

        exec_out = ctx.exec(argv=run_command, cwd=build_dir, output_is_log=True)

        result = RunResult(outputs=[exec_out])
        return result

    def collect(
        self,
        ctx: CollectContext,
    ) -> RecordResult:
        """
        Parse performance metrics from lock benchmark output.

        The output is expected to contain a "measurement" section, preceded by
        a warmup phase which is ignored.

        The collector:
        - Extracts the block following the 'measurement' line
        - Collects all 'total:<int>' values in that block
        - Sums them into a single global_count metric

        Args:
            ctx: CollectContext providing access to the benchmark run output.

        Returns:
            Dictionary containing parsed metrics:
                - global_count: Sum of all totals in the measurement block (int)

        Raises:
            ValueError: If the measurement block or any total entries are missing.

        Example output:
            {
                "global_count": 18482942,
            }
        """
        command_output = ctx.run_result.outputs[-1].stdout

        # Extract measurement block
        m_block = re.search(
            r"(?ms)^\s*measurement\s*$\n(?P<body>.*?)(?:^\s*average\s*:|$\Z)",
            command_output,
        )
        if not m_block:
            raise ValueError(f"Missing 'measurement' block in output:\n{command_output}")

        measurements_str = m_block.group("body")

        totals = [int(x) for x in re.findall(r"total\s*:\s*(\d+)", measurements_str)]
        if not totals:
            raise ValueError(f"No 'total:' entries found in measurement block:\n{command_output}")

        total_ops = sum(totals)

        result_dict = {
            "global_count": total_ops,
        }
        return result_dict

    @staticmethod
    def dependencies() -> list[PackageDependency]:
        """
        List system package dependencies required to build and run Will it scale.

        Returns:
            List of PackageDependency objects for required system packages.
            These are Ubuntu/Debian package names; other distributions may have
            different package names.

        Dependencies include:
            - build-essential: C/C++ compiler and build tools
            - hwlock: Hardware locality library for CPU topology information
        """
        return [
            PackageDependency("build-essential"),
            PackageDependency("hwloc"),
        ]

    @staticmethod
    def supported_tests() -> list[str]:
        """
        Return the list of all supported Will-it-scale process tests.
        """
        return [
            "brk1_processes",
            "brk2_processes",
            "context_switch1_processes",
            "dup1_processes",
            "eventfd1_processes",
            "fallocate1_processes",
            "fallocate2_processes",
            "futex1_processes",
            "futex2_processes",
            "futex3_processes",
            "futex4_processes",
            "getppid1_processes",
            "lock1_processes",
            "lock2_processes",
            "lseek1_processes",
            "lseek2_processes",
            "malloc1_processes",
            "malloc2_processes",
            "mmap1_processes",
            "mmap2_processes",
            "open1_processes",
            "open2_processes",
            "open3_processes",
            "page_fault1_processes",
            "page_fault2_processes",
            "page_fault3_processes",
            "pipe1_processes",
            "poll1_processes",
            "poll2_processes",
            "posix_semaphore1_processes",
            "pread1_processes",
            "pread2_processes",
            "pread3_processes",
            "pthread_mutex1_processes",
            "pthread_mutex2_processes",
            "pthread_mutex3_processes",
            "pthread_mutex4_processes",
            "pthread_mutex5_processes",
            "pwrite1_processes",
            "pwrite2_processes",
            "pwrite3_processes",
            "read1_processes",
            "read2_processes",
            "read3_processes",
            "read4_processes",
            "readseek1_processes",
            "readseek2_processes",
            "readseek3_processes",
            "sched_yield_processes",
            "signal1_processes",
            "tlb_flush1_processes",
            "tlb_flush2_processes",
            "tlb_flush3_processes",
            "unix1_processes",
            "unlink1_processes",
            "unlink2_processes",
            "write1_processes",
            "writeseek1_processes",
            "writeseek2_processes",
            "writeseek3_processes",
        ]
