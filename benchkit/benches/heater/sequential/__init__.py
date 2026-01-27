# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Heater sequential microbenchmark for benchkit.

This benchmark is a tiny CPU "heater" that runs a tight loop for a fixed
duration and reports the number of "operations performed". It is primarily
used to demonstrate benchkit workflows and to characterize per-core behavior
(e.g., sweeping CPU core IDs and plotting ops/core).

Protocol phases (benchkit core protocol):
- fetch: materialize heaterseq.c into a working source directory
- build: compile with gcc -O3
- run: execute for a duration on a given CPU core id
- collect: parse "Operations performed: <N>" from stdout

This module also provides a `heater_seq_campaign()` helper that uses the
new2old compatibility layer to expose a cartesian-product campaign interface
similar to the legacy API, as used in the paper artifacts.

Motivation (hybrid and asymmetric cores):
    This benchmark is particularly useful on modern hybrid-core
    architectures (e.g., ARM big.LITTLE systems or x86 processors with
    P-cores and E-cores such as Intel Alder Lake and newer designs).

    On such platforms, even single-threaded workloads may exhibit
    significant run-to-run performance variability under default Linux
    scheduling, depending on the core on which execution starts and
    whether migrations occur between heterogeneous cores.

    By sweeping CPU core IDs explicitly, the sequential heater enables
    a per-core performance characterization (a "CPU heatmap") that
    reveals systematic differences between fast and slow cores.
    This helps attribute observed variability to underlying hardware
    asymmetry and validate the impact of affinity and placement control.

Platform notes:
    This benchmark is designed to produce meaningful results on Linux.

    Although it will execute on other operating systems (e.g., macOS),
    CPU affinity is not enforced by the scheduler in the same way.
    As a result, the reported per-core measurements may be misleading
    or incorrect on non-Linux platforms, since the process may migrate
    freely across cores despite the requested affinity.
"""

import re
from pathlib import Path
from typing import Iterable

from benchkit.campaign import CampaignCartesianProduct
from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.core.compat.new2old import CampaignCartesianProduct as CampaignCartesianProductNew
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.utils.dir import get_benches_dir, get_results_dir
from benchkit.utils.types import PathType

# Tracked C source lives next to this module to keep it easy to build/debug
# independently during development.
_HEATER_C = (Path(__file__).parent.resolve() / "heaterseq.c").read_text()


class HeaterSequentialBench:
    """
    Sequential heater microbenchmark (benchkit core protocol).

    The underlying C program:
        - sets CPU affinity internally via sched_setaffinity()
        - runs for a user-provided duration in seconds
        - prints a single metric to stdout:
              "Operations performed: <N>"

    Notes:
        - `fetch()` does not pull from the internet. It materializes the tracked
          `heaterseq.c` into a workspace directory (writable, remote-friendly).
        - `build()` compiles into `src_dir` (for simplicity).
    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Path | None = None,
        name: str = "heater_sequential",
    ) -> FetchResult:
        """
        Materialize benchmark sources into a workspace directory.

        The tracked `heaterseq.c` file (located next to this Python module) is
        copied/written into:
            <parent_dir>/<name>/heaterseq.c

        Args:
            ctx: FetchContext providing access to the platform and filesystem helpers.
            parent_dir: Base directory for materialized sources. If None, a benchkit
                default is selected via `get_benches_dir()`.
            name: Subdirectory name under parent_dir.

        Returns:
            FetchResult: contains `src_dir`, the directory holding heaterseq.c.
        """
        parent_dir = get_benches_dir(parent_dir=parent_dir)
        src_dir = parent_dir / name
        ctx.platform.comm.makedirs(src_dir, exist_ok=True)

        heater_c = src_dir / "heaterseq.c"
        if not ctx.platform.comm.isfile(heater_c):
            ctx.platform.comm.write_content_to_file(content=_HEATER_C, output_filename=heater_c)

        return FetchResult(src_dir=src_dir)

    def build(self, ctx: BuildContext) -> BuildResult:
        """
        Compile heaterseq.c into an executable.

        Args:
            ctx: BuildContext providing platform and fetch_result.

        Returns:
            BuildResult: contains `build_dir` (here: same as src_dir) and `other["exe"]`
            pointing to the compiled executable.
        """
        platform = ctx.platform
        src_dir = ctx.fetch_result.src_dir

        # For this microbenchmark, we compile in-place in src_dir.
        # This keeps things simple and makes it easy to inspect artifacts.
        obj_dir = src_dir

        exe_path = obj_dir / "heaterseq"
        if not platform.comm.isfile(exe_path):
            ctx.exec(
                argv=["gcc", "-O3", "-o", str(exe_path), str(src_dir / "heaterseq.c")],
                cwd=obj_dir,
                output_is_log=True,
            )

        return BuildResult(
            build_dir=obj_dir,
            other={"exe": exe_path},
        )

    def run(
        self,
        ctx: RunContext,
        cpu: int,
    ) -> RunResult:
        """
        Execute the heater binary for the configured duration on a given CPU core.

        Args:
            ctx: RunContext. `ctx.duration_s` must be set (seconds; may be float).
            cpu: CPU core ID to pin the process to (affinity set inside the program).

        Returns:
            RunResult containing the execution outputs (stdout/stderr).

        Raises:
            ValueError: if ctx.duration_s is not set.
        """
        duration_s = ctx.duration_s
        if duration_s is None:
            raise ValueError("HeaterSequentialBench requires ctx.duration_s to be set.")

        exe = ctx.build_result.other["exe"]
        exec_out = ctx.exec(
            argv=[str(exe), f"{duration_s}", f"{cpu}"],
            cwd=ctx.build_result.build_dir,
            output_is_log=True,
        )
        return RunResult(outputs=[exec_out])

    def collect(self, ctx: CollectContext) -> RecordResult:
        """
        Parse the ops metric from the benchmark output.

        Expected stdout line:
            "Operations performed: <N>"

        Args:
            ctx: CollectContext providing access to run_result outputs.

        Returns:
            RecordResult with a single field:
                - ops: int

        Raises:
            ValueError: if the expected line cannot be found.
        """
        out = ctx.run_result.outputs[-1].stdout
        m = re.search(r"Operations performed:\s*(\d+)", out)
        if not m:
            raise ValueError(f"Could not parse ops from output:\n{out}")
        return {"ops": int(m.group(1))}

    @staticmethod
    def dependencies() -> list[PackageDependency]:
        """
        System dependencies required to build and run this benchmark.

        Returns:
            List of PackageDependency entries (Debian/Ubuntu package names).
        """
        return [PackageDependency("gcc")]


def heater_seq_campaign(
    name: str = "sequential_heater_campaign",
    results_dir: PathType | None = None,
    platform: Platform | None = None,
    nb_runs: int = 1,
    duration_s: int = 5,
    cpu: Iterable[int] = (0,),
) -> CampaignCartesianProduct:
    """
    Create a cartesian-product campaign for the sequential heater benchmark.

    This helper implements the following experiment protocol:
    - parameter sweep over CPU core IDs
    - fixed duration per run
    - repeated runs (nb_runs) for stability

    Internally this uses the new2old compatibility layer to expose a legacy-like
    CampaignCartesianProduct interface while running the new core protocol.

    Args:
        name: Campaign name.
        results_dir: Directory where results are stored. If None, a benchkit default
            is selected via `get_results_dir()`.
        platform: Optional platform override (local/remote).
        nb_runs: Number of repetitions per parameter point.
        duration_s: Duration of each run in seconds.
        cpu: Iterable of CPU core IDs to sweep (e.g., range(0, os.cpu_count())).

    Returns:
        CampaignCartesianProductNew configured for the sequential heater benchmark.
    """
    results_dir = get_results_dir(results_dir=results_dir)
    benchmark = HeaterSequentialBench()

    return CampaignCartesianProductNew(
        name=name,
        benchmark=benchmark,
        variables={"cpu": cpu},
        nb_runs=nb_runs,
        duration_s=duration_s,
        results_dir=results_dir,
        platform=platform,
    )
