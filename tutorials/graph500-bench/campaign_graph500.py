#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Example of campaign script for Graph500 benchmarks.
"""

from graph500 import graph500_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""

    # Where is the benchmark code located
    graph500_src_dir = (get_curdir(__file__) / "deps/graph500/").resolve()

    # Define the campaign, associated with the Graph500 benchmark
    campaign = graph500_campaign(
        src_dir=graph500_src_dir,
        version=[
            "bfs",
            "bfs_sssp"
        ],
        nb_runs=3,
        benchmark_duration_seconds=3,
        scale=[1,2,4,8],
        non_power_of_two=[False]
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
