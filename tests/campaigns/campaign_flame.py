#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Flamegraph test campaign.

Two sub-campaigns exercise perf-based flame graph generation:

  1. **sleep** — a workload that produces zero CPU samples.
     Validates the graceful no-samples path (warning instead of crash).

  2. **dd** — a CPU-intensive workload (dd if=/dev/urandom of=/dev/null).
     Validates actual flamegraph SVG generation with real perf data.
"""

from benchkit import CampaignCartesianProduct
from benchkit.benches.small.dd import DDBench
from benchkit.benches.small.sleep import SleepBench
from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import PerfRecordWrap, enable_non_sudo_perf
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import get_tools_dir


def _make_flame_post_hook(perf_wrapper):
    """Return a post-run hook that generates a flame graph for each run."""

    def hook(
        experiment_results_lines,
        record_data_dir,
        write_record_file_fun,
    ):
        return perf_wrapper.post_run_hook_flamegraph(
            experiment_results_lines=experiment_results_lines,
            record_data_dir=record_data_dir,
            write_record_file_fun=write_record_file_fun,
            flamegraph_width=400,
            flamegraph_fontsize=14,
        )

    return hook


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    flamegraph_dir = get_tools_dir(None) / "FlameGraph"

    # --- shared perf wrapper (one instance is fine for sequential campaigns) ---
    perf_wrapper = PerfRecordWrap(
        freq=99,
        report_interactive=False,
        report_file=True,
        flamegraph_path=flamegraph_dir,
    )
    perf_wrapper.fetch_flamegraph()

    flame_hook = _make_flame_post_hook(perf_wrapper)

    # --- Campaign 1: sleep (no CPU samples → graceful skip) ---
    campaign_sleep = CampaignCartesianProduct(
        name="flame_sleep",
        benchmark=SleepBench(),
        variables={
            "duration_seconds": [1],
        },
        nb_runs=1,
        command_wrappers=[perf_wrapper],
        post_run_hooks=[
            perf_wrapper.post_run_hook_report,
            flame_hook,
        ],
        platform=platform,
    )

    # --- Campaign 2: dd (CPU-intensive → real flamegraph) ---
    campaign_dd = CampaignCartesianProduct(
        name="flame_dd",
        benchmark=DDBench(),
        variables={
            "block_count": [50],
        },
        nb_runs=1,
        command_wrappers=[perf_wrapper],
        post_run_hooks=[
            perf_wrapper.post_run_hook_report,
            flame_hook,
        ],
        platform=platform,
    )

    suite = CampaignSuite(campaigns=[campaign_sleep, campaign_dd])
    suite.run_suite()


if __name__ == "__main__":
    main()
