# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
KyotoCabinet benchmark implementation for benchkit.

This module implements the benchkit protocol for KyotoCabinet's bundled
`benchmark` program. KyotoCabinet is an embedded key-value store designed
for high-performance storage and retrieval, and is commonly used to study
the behavior of in-memory and on-disk data structures under concurrent load.

The implementation covers:
- Fetching a specific KyotoCabinet release via a source tarball
- Applying local patches to the extracted source tree
- Building the KyotoCabinet library and benchmark binary using autotools
- Running duration-based benchmark workloads with a configurable thread count
- Parsing aggregate performance metrics from the benchmark output

The benchmark output is expected to contain a summary line of the form:

    Summary: total_ops=<N>

from which total operation counts and throughput are derived.

Example:
    >>> from pathlib import Path
    >>> bench = KyotoCabinetBench()
    # ------------------------------------------------------------------
    # Fetch: download and extract KyotoCabinet sources
    # ------------------------------------------------------------------
    >>> fetch_ctx = FetchContext.from_args(
    ...     fetch_args={
    ...         "parent_dir": Path("/tmp/src"),
    ...         "patches": [],
    ...     }
    ... )
    >>> fetch_result = bench.fetch(ctx=fetch_ctx, **fetch_ctx.fetch_args)
    # ------------------------------------------------------------------
    # Build: configure and compile the benchmark binary
    # ------------------------------------------------------------------
    >>> build_ctx = BuildContext.from_fetch(
    ...     fetch_ctx=fetch_ctx,
    ...     fetch_result=fetch_result,
    ... )
    >>> build_result = bench.build(ctx=build_ctx)
    # ------------------------------------------------------------------
    # Run: execute the benchmark for a fixed duration
    # ------------------------------------------------------------------
    >>> run_ctx = RunContext.from_build(
    ...     build_ctx=build_ctx,
    ...     build_result=build_result,
    ...     duration_s=1.0,
    ... )
    >>> run_result = bench.run(
    ...     ctx=run_ctx,
    ...     nb_threads=4,
    ... )
    # ------------------------------------------------------------------
    # Collect: extract performance metrics from benchmark output
    # ------------------------------------------------------------------
    >>> collect_ctx = CollectContext.from_run(
    ...     run_ctx=run_ctx,
    ...     run_result=run_result,
    ... )
    >>> record = bench.collect(ctx=collect_ctx)
    >>> record["operations/second"]
    5000
"""


import re
from pathlib import Path
from typing import Iterable

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.buildtools import make
from benchkit.utils.fetchtools import curl, git_apply_patches, tar_extract


class KyotoCabinetBench:
    """
    Benchmark implementation for KyotoCabinet's benchmark tool.

    This class implements all phases of the benchkit protocol:
    - fetch: Download and extract a KyotoCabinet release tarball and apply patches
    - build: Configure and compile the KyotoCabinet library and benchmark binary
    - run: Execute the benchmark workload for a fixed duration and thread count
    - collect: Parse aggregate performance metrics from the benchmark output
    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Path,
        patches: Iterable[Path] = (),
    ) -> FetchResult:
        """
        Fetch and prepare the KyotoCabinet source tree.

        Downloads the KyotoCabinet release tarball, extracts it into a
        source directory, and applies a sequence of local patches.
        The fetch step is idempotent: if the destination directory already
        exists, no download, extraction, or patching is performed.

        Args:
            ctx: FetchContext providing platform and execution capabilities.
            parent_dir: Parent directory under which the KyotoCabinet source
                directory will be created.
            patches: Iterable of patch files to apply to the extracted source,
                in order.

        Returns:
            FetchResult containing:
                - src_dir: Path to the extracted and patched KyotoCabinet
                  source directory.
        """
        platform = ctx.platform
        comm = platform.comm
        deps_dir = parent_dir / "kyotocabinet"
        kyoto_dir = deps_dir / "kyotocabinet-1.2.76"

        if not comm.isdir(deps_dir):
            comm.makedirs(path=deps_dir, exist_ok=True)

            kyoto_archive = curl(
                ctx=ctx,
                url="https://dbmx.net/kyotocabinet/pkg/kyotocabinet-1.2.76.tar.gz",
                parent_dir=deps_dir,
                name="kyotocabinet-1.2.76.tar.gz",
            )

            tar_extract(
                ctx=ctx,
                archive=kyoto_archive,
            )

            git_apply_patches(
                ctx=ctx,
                repo_dir=kyoto_dir,
                patches=patches,
            )

        return FetchResult(src_dir=kyoto_dir)

    def build(
        self,
        ctx: BuildContext,
    ) -> BuildResult:
        """
        Build the KyotoCabinet benchmark binaries.

        Configures and compiles the KyotoCabinet source tree if it has not
        already been built. The build is performed in-tree using the standard
        autotools workflow.

        The method ensures that:
            - `./configure` is executed if no Makefile is present
            - the main KyotoCabinet library and tools are built
            - the `benchmark` binary is available for the run phase

        The build step is idempotent: if the benchmark binary already exists,
        no recompilation is performed, as no build parameters are currently varied.


        Args:
            ctx: BuildContext providing platform access, fetch results, and
                execution capabilities.

        Returns:
            BuildResult containing:
                - build_dir: Path to the directory where the benchmark binary
                  and shared libraries were built (the source directory).
        """
        platform = ctx.platform
        src_dir = ctx.fetch_result.src_dir
        makefile = src_dir / "Makefile"
        db_bench_path = src_dir / "benchmark"

        if not platform.comm.isfile(makefile):
            ctx.exec(argv=["./configure"], cwd=src_dir)

        if not platform.comm.isfile(db_bench_path):
            make(
                ctx=ctx,
                src_dir=src_dir,
                targets=[""],
                options={},
            )
            make(
                ctx=ctx,
                src_dir=src_dir,
                targets=["benchmark"],
                options={},
            )

        result = BuildResult(
            build_dir=src_dir,
        )
        return result

    def run(
        self,
        ctx: RunContext,
        nb_threads: int = 2,
    ) -> RunResult:
        """
        Execute the KyotoCabinet benchmark workload.

        Runs the `benchmark` binary produced during the build phase using a
        duration-based execution model. The benchmark is executed from the
        build directory and configured to use the specified number of threads.

        The dynamic linker path is explicitly set so the locally built
        KyotoCabinet shared library can be resolved at runtime.

        Args:
            ctx: RunContext providing the build result, execution duration, and
                execution capabilities.
            nb_threads: Number of worker threads used by the benchmark
                (default: 2).

        Returns:
            RunResult containing the execution output from the benchmark
            process, including stdout, stderr, return code, and measured
            wall-clock duration.
        """
        duration_s = ctx.duration_s
        build_dir = ctx.build_result.build_dir

        run_command = [
            "./benchmark",
            "-t",
            str(nb_threads),
            "-d",
            str(duration_s),
        ]

        exec_out = ctx.exec(
            argv=run_command,
            cwd=build_dir,
            env={"LD_LIBRARY_PATH": str(build_dir)},
            output_is_log=True,
        )

        return RunResult(outputs=[exec_out])

    def collect(self, ctx: CollectContext) -> RecordResult:
        """
        Parse performance metrics from KyotoCabinet benchmark output.

        This collector extracts aggregate operation counts from the patched
        KyotoCabinet benchmark output, specifically the summary line of the form:

            Summary: total_ops=<N>

        In addition, it records the measured wall-clock execution time as
        reported by the executor and derives throughput metrics.

        When present, the following optional counters are also extracted:
            - total_update: Total number of update operations performed
            - total_get: Total number of get operations performed

        The execution duration is taken from the `ExecOutput.duration_s` field,
        which reflects the actual runtime of the benchmark rather than the
        requested duration.

        Args:
            ctx: CollectContext providing access to the run result produced by
                the KyotoCabinet benchmark.

        Returns:
            Dictionary containing parsed performance metrics:
                - duration: Wall-clock execution time in seconds
                - global_count: Total number of operations performed
                - operations/second: Throughput in operations per second
                - total_update: Total update operations (if reported)
                - total_get: Total get operations (if reported)

        Raises:
            ValueError: If the expected `Summary: total_ops=...` line is missing
                from the benchmark output.
        """
        output = ctx.run_result.outputs[-1].stdout

        duration_s = ctx.run_result.outputs[0].duration_s

        m_ops = re.search(r"^Summary:\s*total_ops=(\d+)\s*$", output, flags=re.MULTILINE)
        if not m_ops:
            raise ValueError(f"Missing 'Summary: total_ops=...' in kyotocabinet output:\n{output}")

        total_ops = int(m_ops.group(1))

        record: RecordResult = {
            "duration": duration_s,
            "global_count": total_ops,
            "operations/second": (total_ops / duration_s) if duration_s > 0 else 0.0,
        }

        m_upd = re.search(r"^total_update\s*=\s*(\d+)\s*$", output, flags=re.MULTILINE)
        if m_upd:
            record["total_update"] = int(m_upd.group(1))

        m_get = re.search(r"^total_get\s*=\s*(\d+)\s*$", output, flags=re.MULTILINE)
        if m_get:
            record["total_get"] = int(m_get.group(1))

        return record

    @staticmethod
    def dependencies() -> list[PackageDependency]:
        """
        List system package dependencies required to build and run Kyoto Cabinet benchmark.

        Returns:
            List of PackageDependency objects for required system packages.
            These are Ubuntu/Debian package names; other distributions may have
            different package names.

        Dependencies include:
            - build-essential: C/C++ compiler and build tools
        """
        return [
            PackageDependency("build-essential"),
        ]
