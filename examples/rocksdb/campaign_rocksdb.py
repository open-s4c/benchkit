#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for RocksDB benchmark.
"""

from rocksdb import rocksdb_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""
    rocksdb_src_dir = (get_curdir(__file__) / "deps/rocksdb/").resolve()

    campaign = rocksdb_campaign(
        src_dir=rocksdb_src_dir,
        bench_name=["readrandom"],
        nb_runs=1,
        benchmark_duration_seconds=3,
        nb_threads=[2, 4, 8],
    )

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="bench_name",
    )


if __name__ == "__main__":
    main()
