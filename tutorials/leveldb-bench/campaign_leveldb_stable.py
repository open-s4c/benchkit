#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for LevelDB benchmarks with the stabilization "predlinux" tools enabled.
"""

from leveldb import leveldb_campaign

from benchkit.campaign import CampaignSuite
from benchkit.helpers.linux.predictable.predlinux import PredLinux
from benchkit.utils.dir import get_curdir

PRED = True


def main() -> None:
    """Main function of the campaign script."""

    # Where is the benchmark code located
    leveldb_src_dir = (get_curdir(__file__) / "deps/leveldb/").resolve()

    # Define the campaign, associated with the LevelDB benchmark
    campaign = leveldb_campaign(
        src_dir=leveldb_src_dir,
        bench_name=["readrandom"],
        nb_runs=3,
        benchmark_duration_seconds=2,
        nb_threads=[8],
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()

    if PRED:
        ppl = PredLinux()
        ppl.preddo(
            frequency_to_set=None,
            expected_nb_isolated_cpus=0,
            bypass_isolation_check=True,
        )

    suite.run_suite()

    # Generate a graph to visualize the results
    suite.generate_graph(
        plot_name="stripplot",
        x="rep",
        y="throughput",
        hue="bench_name",
    )


if __name__ == "__main__":
    main()
