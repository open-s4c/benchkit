#!/usr/bin/env python3
# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Campaign for the APUE Figure 3.6 I/O Efficiency experiment.

Sweeps BUFFSIZE from 16 to 524288 (powers of two, 16 values) and measures
user CPU, system CPU, wall-clock time, and number of read() loops for
copying a ~493 MiB file from stdin to /dev/null.

Usage:
    python3 campaign_apue_io.py

Results are written to ~/.benchkit/results/ as a CSV file.
"""

from benchmark import ApueIOBench

from benchkit.campaign import CampaignSuite
from benchkit.core.compat.new2old import CampaignCartesianProduct


def main() -> None:
    nb_runs = 5

    # APUE BUFFSIZE sweep: 2^4 .. 2^19 = 16 .. 524288 (16 values)
    # We skip 1, 2, 4, 8 because they cause ~500M+ syscalls and are very slow.
    buffsizes = [2**k for k in range(4, 20)]

    bench = ApueIOBench()

    campaign = CampaignCartesianProduct(
        benchmark=bench,
        variables={
            "buffsize": buffsizes,
        },
        pretty={
            "buffsize": {bs: f"{bs:,}" for bs in buffsizes},
        },
        name="apue_io_efficiency",
        nb_runs=nb_runs,
    )

    suite = CampaignSuite(campaigns=[campaign])
    suite.run_suite()

    def log2_xaxis(chart) -> None:
        chart.set_xscale("log", base=2)

    suite.generate_graph(
        plot_name="lineplot",
        title=f"APUE I/O Efficiency ({nb_runs} runs)",
        x="buffsize",
        y="elapsed_s",
        marker="o",
        process_chart=log2_xaxis,
    )


if __name__ == "__main__":
    main()
