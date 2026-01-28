# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
SPEC CPU® 2017 benchmark integration for benchkit.

This module implements the benchkit protocol for the SPEC CPU 2017 benchmark
suite. SPEC CPU 2017 is a standardized, compute-intensive benchmark used to
evaluate processor and system performance across a wide range of workloads.

The implementation integrates SPEC into benchkit in a non-interactive,
automatable manner and supports selective benchmark execution.

The workflow covers:
- Fetching and installing SPEC CPU 2017 from a local ISO image
- Building selected SPEC benchmarks using a configurable toolchain
- Executing benchmarks via runcpu/specinvoke
- Collecting basic execution metadata (e.g., runtime duration)

The implementation relies on a fake run during the build phase to discover
the benchmark run directory and exact invocation command, enabling precise
and reproducible execution without hardcoded paths.

**Note:** This integration assumes that the user holds a valid
SPEC CPU® 2017 license and has legally obtained and stored the
SPEC CPU 2017 distribution (via a local ISO image).

This module **does not reimplement** or redistribute any part
of SPEC CPU 2017. Instead, it merely **orchestrates and automates
the execution** of the official SPEC CPU 2017 benchmark suite
using benchkit's workflow and abstractions (fetch/build/run/collect).
All benchmark code, tools, and execution semantics remain those of
the original SPEC CPU 2017 distribution.

Example:
    >>> from pathlib import Path
    >>> bench = SPECSPU2017Bench()
    # ------------------------------------------------------------------
    # Fetch: install SPEC CPU 2017 from ISO
    # ------------------------------------------------------------------
    >>> fetch_ctx = FetchContext.from_args(
    ...     fetch_args={
    ...         "parent_dir": Path("/tmp/spec"),
    ...         "spec_source_iso": Path("/tmp/speccpu2017.iso"),
    ...     }
    ... )
    >>> fetch_result = bench.fetch(ctx=fetch_ctx, **fetch_ctx.fetch_args)
    # ------------------------------------------------------------------
    # Build: build a selected SPEC benchmark
    # ------------------------------------------------------------------
    >>> build_ctx = BuildContext.from_fetch(
    ...     fetch_ctx=fetch_ctx,
    ...     fetch_result=fetch_result,
    ... )
    >>> build_result = bench.build(
    ...     ctx=build_ctx,
    ...     bench_name="500.perlbench_r",
    ...     size="test",
    ... )
    # ------------------------------------------------------------------
    # Run: execute the benchmark
    # ------------------------------------------------------------------
    >>> run_ctx = RunContext.from_build(
    ...     build_ctx=build_ctx,
    ...     build_result=build_result,
    ... )
    >>> run_result = bench.run(ctx=run_ctx)
    # ------------------------------------------------------------------
    # Collect: retrieve execution metadata
    # ------------------------------------------------------------------
    >>> collect_ctx = CollectContext.from_run(
    ...     run_ctx=run_ctx,
    ...     run_result=run_result,
    ... )
    >>> record = bench.collect(
    ...     ctx=collect_ctx,
    ...     bench_name="500.perlbench_r",
    ... )
    >>> record["duration_s"]
"""
import os
import re
from pathlib import Path

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.dir import benchkit_home_dir
from benchkit.utils.fetchtools import fuseiso_mount, fuseiso_umount, sed_edit


class SPECCPU2017Bench:
    """
    Benchmark implementation for the SPEC CPU® 2017 benchmark suite.

    This class integrates SPEC CPU 2017 into the benchkit workflow and
    implements the standard benchmark phases:

    - fetch: Obtain the SPEC CPU 2017 benchmark sources and tooling
    - build: Configure and build selected SPEC benchmarks with a given toolchain
    - run: Execute SPEC workloads directly vie the executable
    - collect: Extract the duration_s of the runtime

    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Path,
        spec_source_iso: Path,
    ) -> FetchResult:
        """
        Install the SPEC CPU® 2017 suite into the bench workspace from a local ISO.

        This fetch step does **not** clone anything from GitHub. Instead it:
        - creates `<parent_dir>/spec` if needed
        - mounts `spec_source_iso` via FUSE (no sudo)
        - runs SPEC's `install.sh` non-interactively into `<parent_dir>/spec`
        - unmounts the ISO
        - copies `config/Example-gcc-linux-x86.cfg` to `config/config-gcc-linux-x86.cfg`
        - patches the config to use `/usr` instead of the devtoolset path

        If the target directory already exists, it returns immediately.

        Args:
            ctx: FetchContext providing platform and execution capabilities.
            parent_dir: Directory under which the SPEC installation directory
                (`spec`) will be created/used.
            spec_source_iso: Path to the SPEC CPU 2017 ISO image to install from.

        Returns:
            FetchResult with `src_dir` set to the installed SPEC directory
            (`<parent_dir>/spec`).
        """
        mnt_dir = benchkit_home_dir() / "spec-mnt"
        spec_dir = parent_dir / "spec"

        comm = ctx.platform.comm

        if comm.isdir(spec_dir):
            return FetchResult(src_dir=spec_dir)

        if not comm.isdir(spec_dir):
            comm.makedirs(path=spec_dir, exist_ok=True)

        fuseiso_mount(ctx, spec_source_iso, mnt_dir)

        ctx.exec(
            argv=["bash", "-lc", f"yes | ./install.sh -d {spec_dir}"],
            cwd=mnt_dir,
        )

        fuseiso_umount(ctx, mnt_dir)

        # cp config
        # TODO: support ARM
        arch = ctx.platform.architecture
        if arch != "x86_64":
            raise NotImplementedError(f"SPEC CPU 2017 is only supported on x86_64 (got {arch})")

        ctx.exec(
            argv=["cp", "config/Example-gcc-linux-x86.cfg", "config/config-gcc-linux-x86.cfg"],
            cwd=spec_dir,
        )

        # sed config
        sed_edit(
            ctx=ctx,
            base_dir=spec_dir,
            edits=[
                (
                    's#"/opt/rh/devtoolset-9/root/usr"#"/usr"#',
                    Path("config/config-gcc-linux-x86.cfg"),
                ),
            ],
        )

        return FetchResult(src_dir=spec_dir)

    def build(
        self,
        ctx: BuildContext,
        bench_name: str,
        size: str = "test",
    ) -> BuildResult:
        """
        Build a selected SPEC CPU® 2017 benchmark and determine its execution command.

        This build step performs a **fake run** (`runcpu --fake`) to discover:
        - the benchmark run directory
        - the exact executable path and invocation command

        Using this information, it checks whether the benchmark binary already
        exists. If not, it triggers a real SPEC build for the selected benchmark
        and size.

        The extracted run directory and cleaned run command are stored in the
        resulting BuildResult for use during execution.

        Args:
            ctx: BuildContext providing platform access and the result of the
                preceding fetch step.
            bench_name: SPEC benchmark identifier (e.g. "500.perlbench_r").
            size: SPEC workload size to build (e.g. "test", "train", "ref").

        Returns:
            BuildResult containing:
            - build_dir: Path to the SPEC run directory for the benchmark
            - other["run_command"]: The benchmark invocation command with output
              redirections removed
        """
        platform = ctx.platform
        src_dir = ctx.fetch_result.src_dir

        # Do a fake run to obtain the build_dir and run_command
        log = ctx.exec(
            argv=[
                "bash",
                "-lc",
                (
                    "source shrc && "
                    f"runcpu --fake --loose --size {size} "
                    f"--tune base --config config-gcc-linux-x86.cfg {bench_name}"
                ),
            ],
            cwd=src_dir,
        )

        # Search for the build_dir and run_command in the log
        m = re.search(
            r"# Starting run for copy #0\s*\r?\n"
            r"cd (?P<cwd>[^\r\n]+)\s*\r?\n"
            r"(?P<cmd>[^\r\n]+)",
            log.stdout,
            flags=re.MULTILINE,
        )
        if not m:
            raise ValueError("Could not find a 'Starting run for copy #0' block with cd+command.")

        build_dir = Path(m.group("cwd").strip())
        run_command = m.group("cmd").split(">", 1)[0].rstrip()
        exe = build_dir / os.path.basename(run_command.split()[0])

        # Only build the bench if it does not already exist
        if not platform.comm.isfile(exe):
            ctx.exec(
                argv=[
                    "bash",
                    "-lc",
                    (
                        "source shrc && "
                        f"runcpu --loose --size {size} "
                        f"--tune base --config config-gcc-linux-x86.cfg {bench_name}"
                    ),
                ],
                cwd=src_dir,
            )

        result = BuildResult(
            build_dir=build_dir,
            other={
                "run_command": run_command,
            },
        )
        return result

    def run(
        self,
        ctx: RunContext,
    ) -> RunResult:
        """
        Execute a built SPEC CPU® 2017 benchmark run.

        This run step executes the benchmark command discovered during the build
        phase, using the SPEC run directory as the working directory. The command
        is invoked exactly as extracted from the SPEC harness output, with output
        redirections already stripped.

        The full stdout/stderr of the benchmark execution is captured as a log
        artifact.

        Args:
            ctx: RunContext providing platform access and the result of the
                preceding build step, including the run directory and command.

        Returns:
            RunResult containing the execution output captured as a log.
        """
        build_dir = ctx.build_result.build_dir
        run_command = ctx.build_result.other["run_command"]

        exec_out = ctx.exec(argv=run_command, cwd=build_dir, output_is_log=True)

        result = RunResult(outputs=[exec_out])
        return result

    def collect(
        self,
        ctx: CollectContext,
        bench_name: str,
    ) -> RecordResult:
        """
        Collect execution metadata from a SPEC CPU® 2017 benchmark run.

        This collect step currently records only the total execution duration
        obtained from the run phase. No benchmark-specific performance metrics
        are parsed from SPEC output at this stage.

        Args:
            ctx: CollectContext providing access to the results of the run phase.
            bench_name: SPEC benchmark identifier (currently unused, reserved for
                future metric extraction).

        Returns:
            RecordResult containing a dictionary with:
                - duration_s: Total wall-clock execution time in seconds
        """

        duration_s = ctx.run_result.outputs[0].duration_s

        result_dict = {
            "duration_s": duration_s,
        }

        return result_dict

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
        """
        return [
            PackageDependency("build-essential"),
        ]
