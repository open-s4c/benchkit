#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for RocksDB benchmark.
"""

from rocksdb import rocksdb_campaign

from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.speedupstack import SpeedupStackWrapper
from benchkit.lwchart import time_transformation
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""

    rocksdb_src_dir = (get_curdir(__file__) / "deps/rocksdb/").resolve()
    libbpf_tools_dir = (get_curdir(__file__) / "deps/bcc/libbpf-tools/").resolve()

    thread_profiler_dir = (get_curdir(__file__) / "deps/thread-profiler-bpf/src").resolve()

    speedupstackwrapper = SpeedupStackWrapper(
        libbpf_tools_dir,
        thread_profiler_dir,
        granularity=int(1e8),
    )

    campaign = rocksdb_campaign(
        src_dir=rocksdb_src_dir,
        bench_name=[
            "readrandom",
        ],
        nb_runs=5,
        benchmark_duration_seconds=5,
        nb_threads=[1, 2, 4, 8],
        threadprofiler_enabled=[True, False],
        command_wrappers=([speedupstackwrapper] + speedupstackwrapper.command_wrappers()),
        command_attachments=speedupstackwrapper.command_attachments(),
        pre_run_hooks=speedupstackwrapper.pre_run_hooks(),
        post_run_hooks=speedupstackwrapper.post_run_hooks(),
        enable_data_dir=True,
        symlink_latest=True,
    )

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_graph(
        title="Overhead of Measurement",
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="threadprofiler_enabled",
    )


if __name__ == "__main__":
    main()
