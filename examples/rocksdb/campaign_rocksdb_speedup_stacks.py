#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for RocksDB benchmark.
"""

from rocksdb import rocksdb_campaign

from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.speedupstack import SpeedupStackWrapper
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""

    rocksdb_src_dir = (get_curdir(__file__) / "deps/rocksdb/").resolve()
    libbpf_tools_dir = (get_curdir(__file__) / "deps/bcc/libbpf-tools/").resolve()

    speedupstackwrapper = SpeedupStackWrapper(libbpf_tools_dir)

    campaign = rocksdb_campaign(
        src_dir=rocksdb_src_dir,
        bench_name=["readrandom"],
        nb_runs=5,
        benchmark_duration_seconds=3,
        nb_threads=[2, 4, 8],
        command_wrappers=([speedupstackwrapper] + speedupstackwrapper.command_wrappers()),
        command_attachments=speedupstackwrapper.command_attachments(),
        post_run_hooks=speedupstackwrapper.post_run_hooks(),
        enable_data_dir=True,
        symlink_latest=True,
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

    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="klockstat_total_wait_ns",
        hue="bench_name",
    )

    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="avg_offcputime_micro_s",
        hue="bench_name",
    )



if __name__ == "__main__":
    main()
