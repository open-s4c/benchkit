#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for RocksDB benchmark.
"""

from rocksdb import rocksdb_campaign

from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import enable_non_sudo_perf
from benchkit.commandwrappers.speedupstack import SpeedupStackWrapper
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""

    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    rocksdb_src_dir = (get_curdir(__file__) / "deps/rocksdb/").resolve()
    libbpf_tools_dir = (get_curdir(__file__) / "deps/bcc/libbpf-tools/").resolve()

    speedupstackwrapper = SpeedupStackWrapper(libbpf_tools_dir)

    campaign = rocksdb_campaign(
        src_dir=rocksdb_src_dir,
        bench_name=[
            "readrandom",
            # "readmissing",
            # "seekrandom",
            # "multireadrandom",
            # "readwhilewriting",
        ],
        nb_runs=5,
        benchmark_duration_seconds=10,
        nb_threads=[1, 2, 4, 8],
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
        title="Throughput",
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="bench_name",
    )

    suite.generate_graph(
        title="Klockstat",
        plot_name="lineplot",
        x="nb_threads",
        y="klockstat_total_wait_ns",
        hue="bench_name",
    )

    suite.generate_graph(
        title="Offcputime",
        plot_name="lineplot",
        x="nb_threads",
        y="offcputime_avg_micro_s",
        hue="bench_name",
    )

    suite.generate_graph(
        title="Llcstat",
        plot_name="lineplot",
        x="nb_threads",
        y="llcstat_total_nr_misses",
        hue="bench_name",
    )

    suite.generate_graph(
        title="Strace",
        plot_name="lineplot",
        x="nb_threads",
        y="strace_total_time_s",
        hue="bench_name",
    )

    suite.generate_graph(
        title="Perf Lock",
        plot_name="lineplot",
        x="nb_threads",
        y="perf_lock_total_wait_ns",
        hue="bench_name",
    )


if __name__ == "__main__":
    main()
