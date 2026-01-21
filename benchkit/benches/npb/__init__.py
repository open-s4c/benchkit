# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
NAS Parallel Benchmarks (NPB) implementation for benchkit.

This module implements the benchkit protocol for the NAS Parallel Benchmarks
(NPB), a suite of compute-intensive kernels used to evaluate the performance
and scalability of parallel systems. This implementation targets the OpenMP
variant of NPB (e.g., LU, CG, FT, MG, IS), where each kernel is built as a
standalone executable for a chosen problem class.

For more information on NPB, refer to: https://www.nas.nasa.gov/software/npb.html

The implementation covers:
- Fetching the NPB release tarball (currently NPB 3.4.3) and extracting it
- Generating the default build configuration (``config/make.def``)
- Building a selected kernel target for a given problem class via ``make``
- Running the produced binary with ``OMP_NUM_THREADS`` set to the requested value
- Parsing the final NPB "Benchmark Completed" summary block to extract metrics

Example:
    >>> from pathlib import Path
    >>> bench = NPBBench()
    # ------------------------------------------------------------------
    # Fetch: download and extract NPB
    # ------------------------------------------------------------------
    >>> fetch_ctx = FetchContext.from_args(
    ...     fetch_args={
    ...         "parent_dir": Path("/tmp/src"),
    ...     }
    ... )
    >>> fetch_result = bench.fetch(ctx=fetch_ctx, **fetch_ctx.fetch_args)
    # ------------------------------------------------------------------
    # Build: configure and compile a selected kernel for a given class
    # ------------------------------------------------------------------
    >>> build_ctx = BuildContext.from_fetch(
    ...     fetch_ctx=fetch_ctx,
    ...     fetch_result=fetch_result,
    ... )
    >>> build_result = bench.build(
    ...     ctx=build_ctx,
    ...     category="OMP",
    ...     test_name="lu",
    ...     t_class="A",
    ... )
    # ------------------------------------------------------------------
    # Run: execute the built kernel using a chosen thread count
    # ------------------------------------------------------------------
    >>> run_ctx = RunContext.from_build(
    ...     build_ctx=build_ctx,
    ...     build_result=build_result,
    ... )
    >>> run_result = bench.run(
    ...     ctx=run_ctx,
    ...     nb_threads=24,
    ...     test_name="lu",
    ...     t_class="A",
    ... )
    # ------------------------------------------------------------------
    # Collect: parse performance metrics from the NPB output
    # ------------------------------------------------------------------
    >>> collect_ctx = CollectContext.from_run(
    ...     run_ctx=run_ctx,
    ...     run_result=run_result,
    ... )
    >>> record = bench.collect(ctx=collect_ctx)
    >>> record["duration"]
    3.095
"""

import re
from pathlib import Path
from typing import Any, Dict

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.buildtools import make
from benchkit.utils.fetchtools import curl, tar_extract


class NPBBench:
    """
    Benchmark implementation for the NAS Parallel Benchmarks (NPB).

    This class implements all phases of the benchkit protocol for running
    NPB kernels (e.g., LU, CG, FT) from the NPB OpenMP suite:

    - fetch: Download and extract the NPB release tarball (currently NPB 3.4.3).
    - build: Generate the default ``config/make.def`` and build the selected kernel
      target for a given problem class (``make <kernel> CLASS=<class>``).
    - run: Execute the produced binary (``./<kernel>.<class>.x``) with
      ``OMP_NUM_THREADS`` set to the requested thread count.
    - collect: Parse the final NPB "Benchmark Completed" summary block to extract
      runtime, throughput (Mop/s), thread counts, verification status, version, etc.
    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Path,
    ) -> FetchResult:
        """
        Fetch and prepare the NAS Parallel Benchmarks (NPB) source tree.

        Downloads the official NPB release tarball, extracts it under a dedicated
        dependency directory, and returns the extracted source directory.

        The fetch step is idempotent: if the destination dependency directory
        already exists, the download and extraction steps are skipped.

        Args:
            ctx: FetchContext providing platform and execution capabilities.
            parent_dir: Parent directory under which the NPB dependency directory
                will be created (the suite is placed under ``<parent_dir>/npb``).

        Returns:
            FetchResult containing:
                - src_dir: Path to the extracted NPB source directory
                  (e.g., ``.../npb/NPB3.4.3``).
        """
        platform = ctx.platform
        comm = platform.comm
        deps_dir = parent_dir / "npb"
        npb_dir = deps_dir / "NPB3.4.3"

        if not comm.isdir(deps_dir):
            comm.makedirs(path=deps_dir, exist_ok=True)

            npb_archive = curl(
                ctx=ctx,
                url="https://www.nas.nasa.gov/assets/nas/npb/NPB3.4.3.tar.gz",
                parent_dir=deps_dir,
                name="NPB3.4.3.tar.gz",
            )

            tar_extract(
                ctx=ctx,
                archive=npb_archive,
            )

        return FetchResult(src_dir=npb_dir)

    def build(
        self,
        ctx: BuildContext,
        category: str = "OMP",
        test_name: str = "lu",
        t_class: str = "A",
    ) -> BuildResult:
        """
        Configure and build the NAS Parallel Benchmarks (NPB) suite.

        This step prepares the NPB build system by materializing the ``make.def``
        configuration file from the provided template, creates the expected output
        directory, and then builds a selected benchmark kernel for a given problem
        class using ``make``.

        Concretely, it performs:
          1) Copy ``config/make.def.template`` -> ``config/make.def`` (default config)
          2) Ensure the output directory exists (typically ``bin/``)
          3) Run ``make <test_name> CLASS=<t_class>`` in the selected NPB source tree

        Args:
            ctx: BuildContext providing platform, fetch results, and execution capabilities.
            category: NPB variant directory to use (e.g., ``"OMP"``). This selects the
                source tree ``NPB3.4-<category>`` inside the fetched directory.
                Defaults to ``"OMP"``.
            test_name: NPB kernel target to build (e.g., ``"lu"``, ``"cg"``, ``"ft"``).
                This is passed as the make target. Defaults to ``"lu"``.
            t_class: NPB problem class to build (e.g., ``"S"``, ``"W"``, ``"A"``, ``"B"``).
                This is passed as ``CLASS=<t_class>`` to ``make``. Defaults to ``"A"``.

        Returns:
            BuildResult containing:
                - build_dir: Path to the directory where the resulting benchmark
                  binaries are produced (typically ``<src_dir>/bin``).
        """
        platform = ctx.platform

        src_dir = ctx.fetch_result.src_dir / f"NPB3.4-{category}"
        config_dir = src_dir / "config"
        config_tpl_file = config_dir / "make.def.template"
        config_file = config_dir / "make.def"
        config_content = platform.comm.read_file(path=config_tpl_file)
        platform.comm.write_content_to_file(
            content=config_content,
            output_filename=config_file,
        )

        build_dir = src_dir / "bin"
        platform.comm.makedirs(path=build_dir, exist_ok=True)

        make(
            ctx,
            src_dir=src_dir,
            targets=[test_name],
            options={
                "CLASS": t_class,
            },
        )

        result = BuildResult(
            build_dir=build_dir,
        )
        return result

    def run(
        self,
        ctx: RunContext,
        nb_threads: int = 2,
        test_name: str = "lu",
        t_class: str = "A",
    ) -> RunResult:
        """
        Execute an NAS Parallel Benchmarks (NPB) workload.

        Runs a single NPB kernel binary (e.g., ``lu``, ``cg``, ``ft``) built by the
        NPB suite. The executed binary is selected via ``test_name`` and
        ``t_class``

        The number of OpenMP threads is controlled through the ``OMP_NUM_THREADS``
        environment variable.

        Args:
            ctx: RunContext providing platform, build results, and execution
               capabilities. The benchmark is executed from
               ``ctx.build_result.build_dir``.
            nb_threads: Number of threads to use for the OpenMP run (sets
               ``OMP_NUM_THREADS``). Defaults to 2.
            test_name: NPB kernel name to run (e.g., ``"lu"``, ``"cg"``, ``"ft"``).
               Defaults to ``"lu"``.
            t_class: NPB problem class to run (e.g., ``"S"``, ``"W"``, ``"A"``,
               ``"B"``, ...). Defaults to ``"A"``.

        Returns:
            RunResult containing the execution output (stdout/stderr) of the NPB run.

        Raises:
            FileNotFoundError: If the expected benchmark binary does not exist in the
               build directory (may be raised by the underlying executor).

        Example:
            >>> run_result = bench.run(
            ...     ctx=run_ctx,
            ...     nb_threads=24,
            ...     test_name="lu",
            ...     t_class="A",
            ... )
        """

        build_dir = ctx.build_result.build_dir

        environment = {"OMP_NUM_THREADS": str(nb_threads)}

        run_command = [f"./{test_name}.{t_class}.x"]

        exec_out = ctx.exec(
            argv=run_command,
            cwd=build_dir,
            env=environment,
            output_is_log=True,
        )

        return RunResult(outputs=[exec_out])

    def collect(self, ctx: CollectContext) -> RecordResult:
        """
        Parse performance metrics from NAS Parallel Benchmarks (NPB) output.

        NPB benchmarks typically print a final, structured summary block at the end
        of execution (often containing problem class, size, iteration count, runtime,
        thread counts, throughput, verification status, version, and compile date).

        This collector extracts metrics from that final "Benchmark Completed" summary
        block. The parsing is whitespace-tolerant and expects the fields to appear in
        the usual NPB order.

        Example summary block (representative across NPB kernels):

            <KERNEL> Benchmark Completed.
            Class           = A
            Size            = ...
            Iterations      = ...
            Time in seconds = ...
            Total threads   = ...
            Avail threads   = ...
            Mop/s total     = ...
            Mop/s/thread    = ...
            Operation type  = ...
            Verification    = ...
            Version         = ...
            Compile date    = ...

        Args:
            ctx: CollectContext providing access to run results (stdout/stderr).
                The benchmark output is read from the last recorded command in the run
                (``ctx.run_result.outputs[-1].stdout``).

        Returns:
            Dictionary containing parsed metrics (when present in the summary block):
                - class: NPB problem class (e.g., "A", "B", ...)
                - size: Problem size string (kernel-specific formatting)
                - iterations: Number of iterations performed
                - duration: Execution time in seconds
                - total_threads: Total number of threads used (e.g., OpenMP threads)
                - avail_threads: Number of available threads reported by NPB
                - mops_total: Aggregate throughput in Mop/s
                - mops_per_thread: Per-thread throughput in Mop/s/thread
                - operation_type: Operation type description string
                - verification: Verification status string (e.g., "SUCCESSFUL")
                - version: NPB version string (e.g., "3.4.3")
                - compile_date: Compile date string as reported by NPB

        Raises:
            ValueError: If no compatible NPB "Benchmark Completed" summary block can be
                found in the output.
        """
        command_output = ctx.run_result.outputs[-1].stdout

        # Match the summary block (whitespace tolerant, order-anchored at "X Benchmark Completed.").
        m = re.search(
            r"LU\s+Benchmark\s+Completed\.\s*\n"
            r"\s*Class\s*=\s*(?P<class>[A-Z])\s*\n"
            r"\s*Size\s*=\s*(?P<size>.+?)\s*\n"
            r"\s*Iterations\s*=\s*(?P<iterations>[0-9]+)\s*\n"
            r"\s*Time\s+in\s+seconds\s*=\s*(?P<seconds>[0-9]+(?:\.[0-9]+)?)\s*\n"
            r"\s*Total\s+threads\s*=\s*(?P<total_threads>[0-9]+)\s*\n"
            r"\s*Avail\s+threads\s*=\s*(?P<avail_threads>[0-9]+)\s*\n"
            r"\s*Mop/s\s+total\s*=\s*(?P<mops_total>[0-9]+(?:\.[0-9]+)?)\s*\n"
            r"\s*Mop/s/thread\s*=\s*(?P<mops_thread>[0-9]+(?:\.[0-9]+)?)\s*\n"
            r"\s*Operation\s+type\s*=\s*(?P<op_type>.+?)\s*\n"
            r"\s*Verification\s*=\s*(?P<verification>.+?)\s*\n"
            r"\s*Version\s*=\s*(?P<version>[0-9]+(?:\.[0-9]+)*)\s*\n"
            r"\s*Compile\s+date\s*=\s*(?P<compile_date>.+?)\s*(?:\n|$)",
            command_output,
            flags=re.MULTILINE,
        )

        if not m:
            raise ValueError(
                "Incoherent output from NPB LU (missing 'LU Benchmark Completed' summary block), "
                f"please check output:\n{command_output}"
            )

        gd: Dict[str, Any] = m.groupdict()

        # Normalize some fields (strip to remove alignment spaces)
        size = gd["size"].strip()
        op_type = gd["op_type"].strip()
        verification = gd["verification"].strip()
        compile_date = gd["compile_date"].strip()

        return {
            "class": gd["class"].strip(),
            "size": size,
            "iterations": int(gd["iterations"]),
            "duration": float(gd["seconds"]),
            "total_threads": int(gd["total_threads"]),
            "avail_threads": int(gd["avail_threads"]),
            "mops_total": float(gd["mops_total"]),
            "mops_per_thread": float(gd["mops_thread"]),
            "operation_type": op_type,
            "verification": verification,
            "version": gd["version"].strip(),
            "compile_date": compile_date,
        }

    @staticmethod
    def dependencies() -> list[PackageDependency]:
        """
        List system package dependencies required to build and run Nas Parallel Benchmark.

        Returns:
            List of PackageDependency objects for required system packages.
            These are Ubuntu/Debian package names; other distributions may have
            different package names.

        Dependencies include:
            - build-essential: C/C++ compiler and build tools
            - gfortran: gcc fortran compiler
        """
        return [
            PackageDependency("build-essential"),
            PackageDependency("gfortran"),
        ]

    @staticmethod
    def supported_categories() -> list[str]:
        """
        Return the list of all supported Will-it-scale process tests.
        """
        return [
            "OMP",
            "MPI",
        ]

    @staticmethod
    def supported_classes() -> list[str]:
        """
        Return the list of all supported Will-it-scale process tests.
        """
        return [
            "S",
            "W",
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
        ]

    @staticmethod
    def supported_tests() -> list[str]:
        """
        Return the list of all supported Will-it-scale process tests.
        """
        return [
            "IS",
            "EP",
            "CG",
            "MG",
            "FT",
            "BT-IO",
            "SP",
            "LU",
            "UA",
            "DC",
            "DT",
        ]
