# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
RocksDB benchmark implementation for benchkit.

This module implements the benchkit protocol for RocksDB's db_bench benchmark tool.
RocksDB is an embedded key-value store optimized for fast storage, commonly used
for benchmarking storage and database performance.

The implementation covers:
- Fetching RocksDB source from GitHub
- Building db_bench and preparing a test database
- Running various RocksDB benchmarks (readrandom, fillseq, etc.)
- Parsing performance metrics from db_bench output

Example:
    >>> from pathlib import Path
    >>> bench = RocksDBBench()
    # ------------------------------------------------------------------
    # Fetch: clone RocksDB sources
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

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.buildtools import build_dir_from_ctx, make
from benchkit.utils.dir import get_benches_dir
from benchkit.utils.fetchtools import git_clone


class RocksDBBench:
    """
    Benchmark implementation for RocksDB's db_bench tool.

    This class implements all phases of the benchkit protocol:
    - fetch: Clone RocksDB from GitHub
    - build: Compile db_bench and create test database
    - run: Execute specified db_bench workload
    - collect: Parse performance metrics from output
    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Path | None = None,
        commit: str = "v10.7.5",
    ) -> FetchResult:
        """
        Fetch RocksDB source code from GitHub.

        Clones the RocksDB repository and checks out the specified commit/tag/branch.
        If no commit is specified, uses the default branch (usually main).

        Args:
            ctx: FetchContext providing platform and execution capabilities.
            parent_dir: Directory where the RocksDB repository will be cloned.
            commit: Git commit hash, tag, or branch name (e.g., "v10.7.5").
                   Empty string means use default branch.

        Returns:
            FetchResult containing the path to the cloned repository.
        """
        parent_dir = get_benches_dir(parent_dir=parent_dir)

        rocksdb_dir = git_clone(
            ctx=ctx,
            url="https://github.com/facebook/rocksdb.git",
            commit=commit,
            parent_dir=parent_dir,
        )
        # TODO potential patches
        return FetchResult(src_dir=rocksdb_dir)

    def build(
        self,
        ctx: BuildContext,
    ) -> BuildResult:
        """
        Build RocksDB's db_bench tool and prepare test database.

        Compiles db_bench in release mode if not already built, then creates and
        populates a test database with fillseq if not already present. The test
        database is reused across runs for consistency.

        Args:
            ctx: BuildContext providing platform, fetch results, and execution capabilities.

        Returns:
            BuildResult containing:
                - build_dir: Path to the build directory (same as source for RocksDB)
                - other["tmpdb_dir"]: Path to the prepared test database directory
        """
        platform = ctx.platform
        src_dir = ctx.fetch_result.src_dir
        db_bench_path = src_dir / "db_bench"
        obj_dir = build_dir_from_ctx(ctx=ctx)
        tmpdb_dir = obj_dir / "tmp" / "benchkit_rocksdb_db"

        if not platform.comm.isfile(db_bench_path):
            make(
                ctx=ctx,
                src_dir=src_dir,
                targets=["release"],
                options={"OBJ_DIR": f"{obj_dir}"},
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
                cwd=src_dir,
                output_is_log=True,
            )

        result = BuildResult(
            build_dir=src_dir,
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
        Execute a RocksDB db_bench workload.

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
            ["-duration", f"{duration_s}"]
            if duration_s is not None
            else ["-num", f"{nb_iterations}"]
        )

        run_command = [
            "./db_bench",
            f"-threads={nb_threads}",
            f"-benchmarks={bench_name}",
            f'-use_existing_db={"1" if use_existing_db else "0"}',
            f"-db={tmpdb_dir}",
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
        Parse performance metrics from db_bench output.

        Extracts metrics from the db_bench summary line, which has format:
        "benchname : X.X micros/op Y.Y ops/sec Z.Z seconds N operations; M.M MB/s (A of B found)"

        Args:
            ctx: CollectContext providing access to run results.
            bench_name: Name of the benchmark that was run (used to identify the summary line).

        Returns:
            Dictionary containing parsed metrics:
                - duration: Execution time in seconds
                - global_count: Total number of operations performed
                - microseconds/operation: Average latency per operation
                - operations/second: Throughput in ops/sec
                - MB/s: Throughput in megabytes per second (or "none" if not reported)
                - ofleft: Number of keys found (for read benchmarks)
                - ofright: Total number of keys searched for

        Raises:
            ValueError: If the expected summary line cannot be found or parsed.

        Example output:
            {
                "duration": 5.2,
                "global_count": 100000,
                "microseconds/operation": 52.0,
                "operations/second": 19230.8,
                "MB/s": 2.5,
                "ofleft": 100000,
                "ofright": 100000,
            }
        """
        command_output = ctx.run_result.outputs[-1].stdout

        for line in command_output.splitlines():
            sline = line.strip()
            if sline.startswith(bench_name):
                number_pattern = r"([0-9]|[.])+"
                m = re.match(
                    pattern=(
                        rf"{bench_name}\s*:\s*"
                        rf"(?P<microspop>{number_pattern})\s+micros/op\s+"
                        rf"(?P<opspsec>{number_pattern})\s+ops/sec\s+"
                        rf"(?P<seconds>{number_pattern})\s+seconds\s+"
                        rf"(?P<ops>{number_pattern})\s+operations\s*;\s+"
                        rf"((?P<mbps>{number_pattern})\s+MB/s)?\s*"
                        rf"[(](?P<ofleft>[0-9]+) "
                        rf"of (?P<ofright>[0-9]+) found[)]"
                    ),
                    string=sline,
                )

                gd = m.groupdict()
                nb_operations = int(gd["ops"])

                if "mbps" in gd and gd["mbps"]:
                    val_mbps = float(gd["mbps"])
                else:
                    val_mbps = "none"

                result_dict = {
                    "duration": float(gd["seconds"]),
                    "global_count": nb_operations,
                    "microseconds/operation": float(gd["microspop"]),
                    "operations/second": float(gd["opspsec"]),
                    "MB/s": val_mbps,
                    "ofleft": int(gd["ofleft"]),
                    "ofright": int(gd["ofright"]),
                }

                return result_dict
        raise ValueError(f"Incoherent output from rocksdb, please check output:\n{command_output}")

    @staticmethod
    def dependencies() -> list[PackageDependency]:
        """
        List system package dependencies required to build and run RocksDB.

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
