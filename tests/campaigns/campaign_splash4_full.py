#!/usr/bin/env python3
# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Full SPLASH-4 campaign: every supported benchmark x a thread-count sweep.

Drives the new-API ``Splash4Bench`` through the compat bridge
``benchkit.core.compat.new2old.CampaignCartesianProduct`` (same pattern as
tests/core/compat/test_leveldb_new2old_wrap.py).

Metric: ``primary_time_us`` = each kernel's headline timing in microseconds. For
most kernels this is the ROI ("Total time without initialization"); a few
(barnes, water-*) report a kernel-specific time, and volrend reports only
per-frame times (``primary_time_us`` is None there). The per-kernel semantics
differ, so read the plot as a per-benchmark scaling curve, not a cross-benchmark
comparison.

Thread sweep is limited to counts that have matching per-thread input files for
barnes / water-* / fmm (n{size}-p{n}, input.{n}.{size}); {1,2,4,8} all exist.
"""

from benchkit.benches.splash4 import Splash4Bench
from benchkit.campaign import CampaignSuite
from benchkit.core.compat.new2old import CampaignCartesianProduct

BENCHMARKS = Splash4Bench.supported_benchmarks()  # all 15
NB_THREADS = [1, 2, 4, 8]
NB_RUNS = 3

# One distinct marker per benchmark (seaborn's default marker set is too small
# for 15 style levels, so pass them explicitly).
MARKERS = ["o", "s", "^", "v", "<", ">", "D", "d", "p", "P", "*", "X", "h", "H", "8"]


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
    # One dot per experiment (nb_runs points per config); benchmark encoded by
    # both colour (hue) and marker shape (style).
    suite.generate_graph(
        plot_name="scatterplot",
        x="nb_threads",
        y="primary_time_us",
        hue="benchmark",
        style="benchmark",
        markers=MARKERS,
    )


if __name__ == "__main__":
    main()
