#!/usr/bin/env python3
# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Campaign: GPU execution-budget calibration on random task sets, run inside a
GPU-enabled pythainer container.

Results land in ./results/ next to this script:
- one CSV per campaign (one row per record), plus a plot;
- one directory per record holding taskset.json, per_task.csv and the
  role-structured experiment_results.json;
- metadata.json in the campaign directory (git revision, kernel, durations).
"""

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")  # write figures, never block on a window

from container import gpu_builder, gpu_platform  # noqa: E402
from taskspin import TaskSpinBench  # noqa: E402

from benchkit import CampaignCartesianProduct  # noqa: E402
from benchkit.campaign import CampaignSuite  # noqa: E402

EXAMPLE_DIR = Path(__file__).parent.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--quick", action="store_true", help="tiny parameter space (smoke test)")
    args = parser.parse_args()

    # 1. Build the container image (cached by docker after the first time).
    gpu_builder().build()

    # 2. Every ctx.exec of the benchmark now runs inside that container.
    platform = gpu_platform(mount_dir=EXAMPLE_DIR)

    if args.quick:
        variables = {"nb_tasks": [2, 4], "total_utilization": [0.5], "seed": [0]}
    else:
        variables = {
            "nb_tasks": [2, 4, 8],
            "total_utilization": [0.2, 0.5, 0.8],
            "seed": range(5),
        }

    # 3. Cartesian campaign over the task-set space (one record per task set).
    campaign = CampaignCartesianProduct(
        name="gpu_tasksets",
        benchmark=TaskSpinBench(src_dir=EXAMPLE_DIR / "src"),
        variables=variables,
        nb_runs=1,
        results_dir=EXAMPLE_DIR / "results",
        platform=platform,
    )
    campaign.run()

    # 4. Plot: column names are referenced without their role prefix.
    CampaignSuite(campaigns=[campaign]).generate_graph(
        plot_name="lineplot",
        x="total_utilization",
        y="worst_ratio",
        hue="nb_tasks",
        marker="o",
        title="Worst job duration / requested WCET",
    )


if __name__ == "__main__":
    main()
