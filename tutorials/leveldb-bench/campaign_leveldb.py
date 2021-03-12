#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for LevelDB benchmarks.
"""

from leveldb import leveldb_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""

    # Where is the benchmark code located
    leveldb_src_dir = (get_curdir(__file__) / "deps/leveldb/").resolve()

    # Define the campaign, associated with the LevelDB benchmark
    campaign = leveldb_campaign(
        src_dir=leveldb_src_dir,
        bench_name=[
            "readrandom",
            "readmissing",
            "readhot",
            "seekrandom",
        ],
        nb_runs=3,
        benchmark_duration_seconds=3,
        nb_threads=[2, 4, 8],
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate a graph to visualize the results
    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="bench_name",
    )


if __name__ == "__main__":
    main()
