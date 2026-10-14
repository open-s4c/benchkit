# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
GPU execution-budget calibration benchmark (benchkit core protocol).

A plain class exposing fetch/build/run/collect: no inheritance needed. Each
record is one random task set; the benchmark measures how accurately the GPU
executes jobs of each task's requested WCET.

Only commands go through `ctx.exec` (and hence run inside the container);
the Python code of each step runs on the host.
"""

import json
from pathlib import Path
from typing import Any, Dict

from tasksets import generate_taskset

from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext


class TaskSpinBench:
    """
    Run the taskspin CUDA microbenchmark on random task sets.
    """

    def __init__(self, src_dir: Path) -> None:
        self._src_dir = Path(src_dir).resolve()

    def fetch(self, ctx: FetchContext) -> FetchResult:
        """
        The sources ship with the example: nothing to download.
        """
        return FetchResult(src_dir=self._src_dir)

    def build(self, ctx: BuildContext) -> BuildResult:
        """
        Compile the CUDA microbenchmark with the container's nvcc.
        """
        src_dir = ctx.fetch_result.src_dir
        build_dir = src_dir.parent / "build"
        build_dir.mkdir(exist_ok=True)
        ctx.exec(
            argv=["nvcc", "-O2", "-o", str(build_dir / "taskspin"), str(src_dir / "taskspin.cu")],
            cwd=src_dir,
            output_is_log=True,
        )
        return BuildResult(build_dir=build_dir)

    def run(
        self,
        ctx: RunContext,
        nb_tasks: int,
        total_utilization: float,
        seed: int,
        nb_jobs: int = 20,
    ) -> RunResult:
        """
        Generate the record's task set (reproducible from its seed), keep it
        in the record directory, and spin one GPU job per requested WCET.
        """
        taskset = generate_taskset(
            nb_tasks=nb_tasks,
            total_utilization=total_utilization,
            seed=seed,
        )
        (ctx.record_dir / "taskset.json").write_text(json.dumps(taskset, indent=2) + "\n")

        wcets = [f"{task['wcet_us']:.3f}" for task in taskset]
        out = ctx.exec(
            argv=[str(ctx.build_result.build_dir / "taskspin"), str(nb_jobs)] + wcets,
            cwd=ctx.build_result.build_dir,
        )
        return RunResult(outputs=[out])

    def collect(self, ctx: CollectContext) -> Dict[str, Any]:
        """
        Keep the per-task measurements in the record directory and return the
        record's aggregates: one run, one record.
        """
        tasks = []
        for line in ctx.run_result.outputs[-1].stdout.splitlines():
            if not line.startswith("task="):
                continue
            fields = dict(kv.split("=") for kv in line.split())
            tasks.append({k: float(v) for k, v in fields.items()})

        per_task_lines = ["task;requested_us;mean_us;max_us"] + [
            f"{int(t['task'])};{t['requested_us']};{t['mean_us']};{t['max_us']}" for t in tasks
        ]
        (ctx.record_dir / "per_task.csv").write_text("\n".join(per_task_lines) + "\n")

        ratios_mean = [t["mean_us"] / t["requested_us"] for t in tasks]
        ratios_max = [t["max_us"] / t["requested_us"] for t in tasks]
        return {
            "mean_ratio": sum(ratios_mean) / len(ratios_mean),
            "worst_ratio": max(ratios_max),
            "total_requested_us": sum(t["requested_us"] for t in tasks),
        }
