#!/usr/bin/env python3
# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Cartesian campaign for the SPLASH-4 suite.

Drives the new-API ``Splash4Bench`` through the compat bridge
``benchkit.core.compat.new2old.CampaignCartesianProduct`` (same pattern as
tests/core/compat/test_leveldb_new2old_wrap.py), sweeping benchmark x thread
count and plotting the ROI (parallel-region) time.
"""

from benchkit.benches.splash4 import Splash4Bench
from benchkit.campaign import CampaignSuite
from benchkit.core.compat.new2old import CampaignCartesianProduct

# Small, quick smoke campaign. See campaign_splash4_full.py for the whole suite.
#   - "lu-nc" (lu-non_contiguous): a low-speedup, barrier-dominated case study.
#   - "fft": a fast, well-scaling reference point.
BENCHMARKS = ["lu-nc", "fft"]
NB_THREADS = [1, 2, 4]
NB_RUNS = 1


def main() -> None:
    campaign = CampaignCartesianProduct(
        benchmark=Splash4Bench(),
        variables={
            "benchmark": BENCHMARKS,
            "nb_threads": NB_THREADS,
        },
        nb_runs=NB_RUNS,
    )

    suite = CampaignSuite(campaigns=[campaign])
    suite.print_durations()
    suite.run_suite()

    suite.generate_global_csv()
    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="time_without_init_us",
        hue="benchmark",
    )


if __name__ == "__main__":
    main()
