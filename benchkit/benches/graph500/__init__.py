# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Graph500 benchmark implementation for benchkit.

Graph500 is a benchmark for large-scale graph traversal and analysis,
measuring performance using TEPS (Traversed Edges Per Second).

The implementation covers:
- Fetching Graph500 source from GitHub
- Building the reference implementation (BFS and BFS+SSSP variants)
- Running graph generation and traversal benchmarks
- Parsing TEPS and perfstat metrics from output
"""

import json
import os
from pathlib import Path
from typing import Any

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.utils.buildtools import build_dir_from_ctx
from benchkit.utils.dir import get_benches_dir
from benchkit.utils.fetchtools import git_clone


class Graph500Bench:
    """
    Benchmark implementation for Graph500.

    Implements the benchkit protocol:
    - fetch: clone from github
    - build: compile reference implementation
    - run: execute graph generation and traversal
    - collect: parse TEPS and perf stat metrics from output
    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Path | None = None,
        commit: str = "newreference",
    ) -> FetchResult:
        """
        Fetch Graph500 source code from GitHub.

        Args:
            ctx: FetchContext providing platform and execution capabilities.
            parent_dir: Directory where the repository will be cloned.
            commit: Git commit, tag, or branch (default: newreference branch).

        Returns:
            FetchResult containing the path to the cloned repository.
        """
        parent_dir = get_benches_dir(parent_dir=parent_dir)

        graph500_dir = git_clone(
            ctx=ctx,
            url="https://github.com/graph500/graph500.git",
            commit=commit,
            parent_dir=parent_dir,
        )

        return FetchResult(src_dir=graph500_dir)

    def build(
        self,
        ctx: BuildContext,
    ) -> BuildResult:
        """Build the Graph500 reference implementation.
        Args:
            ctx: BuildContext providing execution capabilities and build arguments.
        Returns:
            BuildResult containing the path to the build directory.
        """

        platform = ctx.platform

        # copy source to build directory
        src_dir = ctx.fetch_result.src_dir / "src"
        build_dir = build_dir_from_ctx(ctx=ctx)

        platform.comm.shell(
            command=(f"cp -r {src_dir}/. {build_dir}/"),
            output_is_log=True,
        )

        # patch the makefile
        makefile_path = build_dir / "Makefile"
        makefile = platform.comm.read_file(makefile_path)
        lines = makefile.splitlines()

        # ensure -fcommon is in CFLAGS to avoid multiple definition errors on newer GCC versions
        for index, line in enumerate(lines):
            if line.startswith("CFLAGS"):
                if "-fcommon" not in line:
                    lines[index] = line + " -fcommon"

        platform.comm.write_content_to_file(
            "\n".join(lines),
            makefile_path,
        )

        # build the reference implementation (both BFS and BFS+SSSP binaries)
        ctx.exec(
            argv=["make", "-j"],
            cwd=build_dir,
            output_is_log=True,
        )

        return BuildResult(build_dir=build_dir)

    def run(
        self,
        ctx: RunContext,
        version: str = "bfs",
        scale: int = 16,
        skip_validation: bool = False,
        edge_factor: int = 16,
    ) -> RunResult:
        """Run the Graph500 benchmark with specified parameters.
        Args:
            ctx: RunContext providing execution capabilities and run arguments.
            version: Which binary to run - "bfs" or "bfs_sssp   " (default: "bfs").
            scale: Scale factor for graph generation (default: 16).
            skip_validation: Whether to skip validation of results (default: False).
            edge_factor: Average degree of vertices (default: 16).
        Returns:
            RunResult containing the output of the benchmark execution.
        """

        if version not in ["bfs", "bfs_sssp"]:
            raise ValueError(f"Invalid version: {version}. " "Must be 'bfs' or 'bfs_sssp'")

        build_dir = ctx.build_result.build_dir
        validation = "1" if skip_validation else "0"
        home_dir = os.environ.get("HOME", "/tmp")

        # construct the command to run the benchmark
        # with appropriate environment variables and arguments
        command = (
            f"HOME={home_dir} mpirun -np 1"
            f" -x HOME"
            f" -x SKIP_VALIDATION={validation}"
            f"{version == 'bfs_sssp' and ' -x SKIP_BFS=1' or ''}"
            f" ./graph500_reference_{version}"
            f" {scale} {edge_factor}"
        )

        exec_out = ctx.exec(
            argv=["bash", "-c", command],
            cwd=build_dir,
            output_is_log=True,
        )

        return RunResult(outputs=[exec_out])

    def collect(self, ctx: CollectContext) -> RecordResult:
        """Collect and parse the output from the Graph500 benchmark run.
        Args:
            ctx: CollectContext providing access to the run results and arguments.
        Returns:
            RecordResult containing the parsed metrics from the benchmark output.
        """

        # parsing from standard output of the benchmark run
        output = ctx.run_result.outputs[-1].stdout

        parsed: dict[str, Any] = {}

        for line in output.splitlines():
            if ":" not in line:
                continue
            parts = line.split(":")
            if len(parts) < 2:
                continue
            key = "_".join(parts[0].strip().split())
            value_str = parts[-1].replace("!", "").strip()
            try:
                if value_str.lower() == "inf":
                    parsed[key] = float("inf")
                elif value_str.lower() == "nan":
                    parsed[key] = float("nan")
                elif "." not in value_str and "e" not in value_str.lower():
                    parsed[key] = int(value_str)
                else:
                    parsed[key] = float(value_str)
            except ValueError:
                parsed[key] = value_str

        # parsing from the perf stat output if available
        perf_file = None
        results_dir = Path.cwd() / "results"  # can be written elsewhere if desired
        if results_dir.exists():
            perf_files = list(results_dir.glob("**/perf-stat.txt"))
            if perf_files:
                perf_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                perf_file = perf_files[0]

        if perf_file and perf_file.exists():
            try:
                with open(perf_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            event = data.get("event")
                            val_str = data.get("counter-value", "0")
                            if event:
                                parsed[f"perf_{event}"] = float(val_str)
                        except json.JSONDecodeError:
                            continue

                if parsed.get("perf_cycles", 0) > 0:
                    parsed["perf_IPC"] = parsed.get("perf_instructions", 0) / parsed["perf_cycles"]

                if parsed.get("perf_L1-dcache-loads", 0) > 0:
                    parsed["perf_L1_miss_rate"] = (
                        parsed.get("perf_L1-dcache-load-misses", 0) / parsed["perf_L1-dcache-loads"]
                    ) * 100

                if parsed.get("perf_cache-references", 0) > 0:
                    parsed["perf_cache_miss_rate"] = (
                        parsed.get("perf_cache-misses", 0) / parsed["perf_cache-references"]
                    ) * 100

                print(f"[INFO] Successfully parsed perf data from: {perf_file}")

            except Exception as e:
                print(f"[Warning] Failed to parse perf-stat.txt: {e}")
        else:
            print("[Warning] Could not find perf-stat.txt for this run.")

        # keys that are always included, regardless of the used algorithm
        base_keys = [
            "SCALE",
            "edgefactor",
            "NBFS",
            "graph_generation",
            "construction_time",
            "num_mpi_processes",
            "min_nedge",
            "firstquartile_nedge",
            "median_nedge",
            "thirdquartile_nedge",
            "max_nedge",
            "mean_nedge",
            "stddev_nedge",
            "perf_cycles",
            "perf_instructions",
            "perf_IPC",
            "perf_L1-dcache-loads",
            "perf_L1-dcache-load-misses",
            "perf_L1_miss_rate",
            "perf_L1-dcache-stores",
            "perf_L1-dcache-store-misses",
            "perf_l2d_cache_rd",
            "perf_l2d_cache_refill",
            "perf_cache-references",
            "perf_cache-misses",
            "perf_cache_miss_rate",
            "perf_dTLB-load-misses",
            "perf_branch-misses",
            "perf_mem_access_rd",
            "perf_mem_access_wr",
        ]

        version = ctx.run_args.get("version", "bfs")

        # construct the record with appropriate keys
        # based on the version of the benchmark run (BFS or BFS+SSSP)
        if version == "bfs":
            record = {k: parsed.get(k) for k in base_keys}
            record["algorithm"] = "BFS"
            record["edge_factor"] = ctx.run_args.get("edge_factor")
            record["min_time"] = parsed.get("bfs_min_time")
            record["median_time"] = parsed.get("bfs_median_time")
            record["mean_time"] = parsed.get("bfs_mean_time")
            record["stddev_time"] = parsed.get("bfs_stddev_time")
            record["harmonic_mean_TEPS"] = parsed.get("bfs_harmonic_mean_TEPS")
            record["median_TEPS"] = parsed.get("bfs_median_TEPS")
            record["harmonic_stddev_TEPS"] = parsed.get("bfs_harmonic_stddev_TEPS")
            record["mean_validate"] = parsed.get("bfs_mean_validate")
            return record
        else:
            record = {k: parsed.get(k) for k in base_keys}
            record["algorithm"] = "SSSP"
            record["edge_factor"] = ctx.run_args.get("edge_factor")
            record["min_time"] = parsed.get("sssp_min_time")
            record["median_time"] = parsed.get("sssp_median_time")
            record["mean_time"] = parsed.get("sssp_mean_time")
            record["stddev_time"] = parsed.get("sssp_stddev_time")
            record["harmonic_mean_TEPS"] = parsed.get("sssp_harmonic_mean_TEPS")
            record["median_TEPS"] = parsed.get("sssp_median_TEPS")
            record["harmonic_stddev_TEPS"] = parsed.get("sssp_harmonic_stddev_TEPS")
            record["mean_validate"] = parsed.get("sssp_mean_validate")
            return record
