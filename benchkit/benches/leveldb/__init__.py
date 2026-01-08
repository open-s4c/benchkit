# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
LevelDB benchmark implementation for benchkit.

This module implements the benchkit protocol for LevelDB's db_bench benchmark tool.
LevelDB is an embedded key-value store optimized for fast storage, commonly used
for benchmarking storage and database performance.

The implementation covers:
- Fetching LevelDB source from GitHub
- Building db_bench and preparing a test database
- Running various LevelDB benchmarks (readrandom, fillseq, etc.)
- Parsing performance metrics from db_bench output

Example:
    >>> from pathlib import Path
    >>> bench = LevelDBBench()

    # ------------------------------------------------------------------
    # Fetch: clone LevelDB sources
    # ------------------------------------------------------------------
    >>> fetch_ctx = FetchContext.from_args(
    ...     fetch_args={
    ...         "parent_dir": Path("/tmp/src"),
    ...         "commit": "v1.17.0",
    ...     }
    ... )
    >>> fetch_result = bench.fetch(ctx=fetch_ctx, **fetch_ctx.fetch_args)

    # ------------------------------------------------------------------
    # Build: compile db_bench and prepare the test database
    # ------------------------------------------------------------------
    >>> build_ctx = BuildContext.from_fetch(
    ...     fetch_ctx=fetch_ctx,
    ...     fetch_result=fetch_result,
    ... )
    >>> build_result = bench.build(ctx=build_ctx)

    # ------------------------------------------------------------------
    # Run: execute a benchmark workload
    # ------------------------------------------------------------------
    >>> run_ctx = RunContext.from_build(
    ...     build_ctx=build_ctx,
    ...     build_result=build_result,
    ...     duration_s=1.0,
    ... )
    >>> run_result = bench.run(
    ...     ctx=run_ctx,
    ...     bench_name="readrandom",
    ...     nb_threads=4,
    ... )

    # ------------------------------------------------------------------
    # Collect: parse performance metrics from db_bench output
    # ------------------------------------------------------------------
    >>> collect_ctx = CollectContext.from_run(
    ...     run_ctx=run_ctx,
    ...     run_result=run_result,
    ... )
    >>> record = bench.collect(
    ...     ctx=collect_ctx,
    ...     bench_name="readrandom",
    ... )

    >>> record["operations/second"]
    5500

"""

import re
from pathlib import Path
from typing import Iterable

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.buildtools import build_dir_from_ctx, cmake_build
from benchkit.utils.fetchtools import git_clone


class LevelDBBench:
    """
    Benchmark implementation for LevelDB's db_bench tool.

    This class implements all phases of the benchkit protocol:
    - fetch: Clone LevelDB from GitHub
    - build: Compile db_bench and create test database
    - run: Execute specified db_bench workload
    - collect: Parse performance metrics from output
    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Path,
        commit: str = "",
        patches: Iterable[Path] = (),
    ) -> FetchResult:
        """
        Fetch LevelDB source code from GitHub.

        Clones the LevelDB repository and checks out the specified commit/tag/branch.
        If no commit is specified, uses the default branch (usually main).

        Args:
            ctx: FetchContext providing platform and execution capabilities.
            parent_dir: Directory where the LevelDB repository will be cloned.
            commit: Git commit hash, tag, or branch name (e.g., "v10.7.5").
                   Empty string means use default branch.
            patches: Iterable of patch files to apply to the  source, in order.

        Returns:
            FetchResult containing the path to the cloned repository.
        """

        leveldb_dir = git_clone(
            ctx=ctx,
            url="https://github.com/google/leveldb.git",
            commit=commit,
            parent_dir=parent_dir,
            patches=patches,
        )

        ctx.exec(
            argv=["git", "submodule", "update", "--init", "--recursive"],
            cwd=leveldb_dir,
            output_is_log=True,
        )

        ctx.exec(
            argv=["git", "checkout", "v1.17.0"],
            cwd=leveldb_dir / "third_party/googletest",
            output_is_log=True,
        )

        return FetchResult(src_dir=leveldb_dir)

    def build(
        self,
        ctx: BuildContext,
    ) -> BuildResult:
        """
        Build LevelDB's db_bench tool and prepare test database.

        Compiles db_bench in release mode if not already built, then creates and
        populates a test database with fillseq if not already present. The test
        database is reused across runs for consistency.

        Args:
            ctx: BuildContext providing platform, fetch results, and execution capabilities.

        Returns:
            BuildResult containing:
                - build_dir: Path to the build directory (same as source for LevelDB)
                - other["tmpdb_dir"]: Path to the prepared test database directory
        """
        platform = ctx.platform
        src_dir = ctx.fetch_result.src_dir
        db_bench_path = src_dir / "db_bench"
        obj_dir = build_dir_from_ctx(ctx=ctx)
        tmpdb_dir = obj_dir / "tmp" / "benchkit_level_db"

        if not platform.comm.isfile(db_bench_path):
            cmake_build(
                ctx=ctx,
                src_dir=src_dir,
                build_dir=obj_dir,
                build_type="Release",
                target="db_bench",
            )
        if not platform.comm.isdir(tmpdb_dir):
            platform.comm.makedirs(path=tmpdb_dir, exist_ok=True)
            ctx.exec(
                argv=[
                    "./db_bench",
                    "--threads=1",
                    "--benchmarks=fillseq",
                    f"--db={tmpdb_dir}",
                ],
                cwd=obj_dir,
                output_is_log=True,
            )

        result = BuildResult(
            build_dir=obj_dir,
            other={
                "tmpdb_dir": tmpdb_dir,
            },
        )
        return result

    def run(
        self,
        ctx: RunContext,
        bench_name: str,
        nb_threads: int = 2,
        nb_iterations: int = 40000,
    ) -> RunResult:
        """
        Execute a LevelDB db_bench workload.

        Runs the specified benchmark using the pre-populated database from the build phase.
        Supports both duration-based runs (if ctx.duration_s is set) and iteration-based runs.

        Args:
            ctx: RunContext providing platform, build results, and execution capabilities.
            bench_name: Name of the db_bench benchmark to run (e.g., "readrandom", "fillseq").
            nb_threads: Number of threads to use for the benchmark (default: 2).
            nb_iterations: Number of operations if not using duration-based run (default: 40000).

        Returns:
            RunResult containing the execution output from db_bench.

        Example:
            >>> run_result = bench.run(
            ...     ctx=run_ctx,
            ...     bench_name="readrandom",
            ...     nb_threads=4,
            ... )
        """
        use_existing_db = True
        duration_s = ctx.duration_s
        build_dir = ctx.build_result.build_dir
        tmpdb_dir = ctx.build_result.other["tmpdb_dir"]
        workload_args = (
            [f"--duration={duration_s}"] if duration_s is not None else [f"--num={nb_iterations}"]
        )

        run_command = [
            "./db_bench",
            f"--threads={nb_threads}",
            f"--benchmarks={bench_name}",
            f'--use_existing_db={"1" if use_existing_db else "0"}',
            f"--db={tmpdb_dir}",
            *workload_args,
        ]

        exec_out = ctx.exec(argv=run_command, cwd=build_dir, output_is_log=True)

        result = RunResult(outputs=[exec_out])
        return result

    def collect(
        self,
        ctx: CollectContext,
        bench_name: str,
    ) -> RecordResult:
        """
        Parse performance metrics from LevelDB db_bench output.

        This collector is tailored to a patched LevelDB db_bench that emits a
        thread-aware statistics line of the form:

            benchstats:<duration>;<global_count>;<thread_0>;...;<thread_{N-1}>

        where:
            - <duration> is the total execution time reported by db_bench
            - <global_count> is the total number of operations executed
            - <thread_i> is the number of operations executed by thread i

        In addition, the standard db_bench summary line is parsed when present,
        for example:

            readrandom : 1.841 micros/op; (539804 of 1000000 found)

        This line is used to extract per-operation latency and, for read
        benchmarks, the number of keys found.

        Args:
            ctx: CollectContext providing access to the run output produced by
                db_bench.
            bench_name: Name of the benchmark that was run (e.g., "readrandom"),
                used to identify the relevant summary line.

        Returns:
            Dictionary containing parsed metrics, including:
                - duration: Normalized execution time in seconds (derived from
                  benchstats and divided by the number of threads).
                - global_count: Total number of operations performed.
                - operations/second: Throughput in operations per second, computed
                  as global_count / duration.
                - microseconds/operation: Average latency per operation, extracted
                  from the db_bench summary line when available.
                - thread_i: Number of operations executed by thread i (one entry
                  per thread).
                - ofleft: Number of keys found (for read benchmarks, if reported).
                - ofright: Total number of keys searched for (for read benchmarks,
                  if reported).

        Raises:
            ValueError: If the expected benchstats line is missing or inconsistent
                with the number of threads, indicating incoherent db_bench output.

        Example output:
            {
                "duration": 1.0,
                "global_count": 1629644,
                "operations/second": 1629644.0,
                "microseconds/operation": 1.841,
                "thread_0": 542781,
                "thread_1": 539804,
                "thread_2": 547059,
                "ofleft": 539804,
                "ofright": 1000000,
            }
        """
        output = ctx.run_result.outputs[-1].stdout

        # ------------------------------------------------------------------
        # 1) Parse patched benchstats line
        # ------------------------------------------------------------------
        if "benchstats:" not in output:
            raise ValueError(f"Incoherent output from leveldb (missing benchstats line):\n{output}")

        benchstats = output.split("benchstats:")[-1].strip()
        values = benchstats.split(";")

        # Infer number of threads from benchstats format:
        # duration + global_count + N thread fields
        if len(values) < 3:
            raise ValueError(f"Incoherent benchstats format, expected at least 3 fields:\n{output}")

        nb_threads = len(values) - 2

        names = ["duration", "global_count"] + [f"thread_{k}" for k in range(nb_threads)]
        raw = dict(zip(names, values))

        try:
            duration_raw = float(raw["duration"])
            global_count = int(float(raw["global_count"]))
        except ValueError as e:
            raise ValueError(f"Failed to parse numeric benchstats values:\n{output}") from e

        # Historical normalization: duration is divided by number of threads
        duration = duration_raw / nb_threads if nb_threads > 0 else duration_raw

        record: RecordResult = {
            "duration": duration,
            "global_count": global_count,
            "operations/second": (global_count / duration) if duration > 0 else 0.0,
        }

        # Per-thread operation counts
        for k in range(nb_threads):
            try:
                record[f"thread_{k}"] = int(float(raw[f"thread_{k}"]))
            except ValueError as e:
                raise ValueError(
                    f"Failed to parse per-thread count for thread {k}:\n{output}"
                ) from e

        # ------------------------------------------------------------------
        # 2) Parse standard db_bench summary line (latency + found info)
        # ------------------------------------------------------------------
        #
        # Example:
        #   readrandom : 1.841 micros/op; (539804 of 1000000 found)
        #
        summary_re = re.search(
            rf"^{re.escape(bench_name)}\s*:\s*"
            rf"(?P<microspop>[0-9]*\.?[0-9]+)\s+micros/op;?\s*"
            rf"(?:\(\s*(?P<ofleft>\d+)\s+of\s+(?P<ofright>\d+)\s+found\s*\))?",
            output,
            flags=re.MULTILINE,
        )

        if summary_re:
            record["microseconds/operation"] = float(summary_re.group("microspop"))

            if summary_re.group("ofleft") is not None:
                record["ofleft"] = int(summary_re.group("ofleft"))
                record["ofright"] = int(summary_re.group("ofright"))

        return record

    @staticmethod
    def dependencies() -> list[PackageDependency]:
        """
        List system package dependencies required to build and run LevelDB.

        Returns:
            List of PackageDependency objects for required system packages.
            These are Ubuntu/Debian package names; other distributions may have
            different package names.

        Dependencies include:
            - build-essential: C/C++ compiler and build tools
            - libbz2-dev: bzip2 compression library
            - libgflags-dev: Command-line flags library
            - liblz4-dev: LZ4 compression library
            - libsnappy-dev: Snappy compression library
            - libzstd-dev: Zstandard compression library
            - zlib1g-dev: zlib compression library
        """
        return [
            PackageDependency("build-essential"),
            PackageDependency("libbz2-dev"),
            PackageDependency("libgflags-dev"),
            PackageDependency("liblz4-dev"),
            PackageDependency("libsnappy-dev"),
            PackageDependency("libzstd-dev"),
            PackageDependency("zlib1g-dev"),
        ]
