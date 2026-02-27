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
            # "readmissing",
            # TODO: make selection of working benchmarks
            # "fillseq",  # write N values in sequential key order in async mode
            # "fillseqdeterministic",  # write N values in the specified key order and keep
            #  the shape of the LSM tree
            # "fillrandom",  # write N values in random key order in async mode
            # "filluniquerandomdeterministic",  # write N values in a random key order and keep
            #  the shape of the LSM tree
            # "overwrite",  # overwrite N values in random key order in async mode
            # "fillsync",  # write N/1000 values in random key order in sync mode
            # "fill100K",  # write N/1000 100K values in random order in async mode
            # "deleteseq",  # delete N keys in sequential order
            # "deleterandom",  # delete N keys in random order
            # "readseq",  # read N times sequentially
            # "readtocache",  # 1 thread reading database sequentially
            # "readreverse",  # read N times in reverse order
            # "readrandom",  # read N times in random order
            # "readmissing",  # read N missing keys in random order
            # "readwhilewriting",  # 1 writer, N threads doing random reads
            # "readwhilemerging",  # 1 merger, N threads doing random reads
            # "readwhilescanning",  # 1 thread doing full table scan, N threads doing random reads
            # "readrandomwriterandom",  # N threads doing random-read, random-write
            # "updaterandom",  # N threads doing read-modify-write for random keys
            # "xorupdaterandom",  # N threads doing read-XOR-write for random keys
            # "appendrandom",  # N threads doing read-modify-write with growing values
            # "mergerandom",  # same as updaterandom/appendrandom using merge operator.
            #  Must be used with merge_operator
            # "readrandommergerandom",  # perform N random read-or-merge operations.
            #  Must be used with merge_operator
            # "newiterator",  # repeated iterator creation
            # "seekrandom",  # N random seeks, call Next seek_nexts times per seek
            # "seekrandomwhilewriting",  # seekrandom and 1 thread doing overwrite
            # "seekrandomwhilemerging",  # seekrandom and 1 thread doing merge
            # "crc32c",  # repeated crc32c of <block size> data
            # "xxhash",  # repeated xxHash of <block size> data
            # "xxhash64",  # repeated xxHash64 of <block size> data
            # "xxh3",  # repeated XXH3 of <block size> data
            # "acquireload",  # load N*1000 times
            # "fillseekseq",  # write N values in sequential key, then read them by
            #  seeking to each key
            # "randomtransaction",  # execute N random transactions and verify correctness
            # "randomreplacekeys",  # randomly replaces N keys by deleting the old version
            #  and putting the new version
            # "timeseries",  # 1 writer generates time series data and multiple readers
            #  doing random reads on id
        ],
        nb_runs=1,
        benchmark_duration_seconds=3,
        nb_threads=[1, 2, 4, 8],
        # nb_threads=[1, 2],
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

    # suite.generate_graph(
    #     title="Throughput",
    #     plot_name="lineplot",
    #     x="nb_threads",
    #     y="throughput",
    #     hue="bench_name",
    # )

    # suite.generate_graph(
    #     title="Klockstat",
    #     plot_name="lineplot",
    #     x="nb_threads",
    #     y="klockstat_total_wait_ns",
    #     hue="bench_name",
    # )

    # suite.generate_graph(
    #     title="Offcputime",
    #     plot_name="lineplot",
    #     x="nb_threads",
    #     y="offcputime_avg_micro_s",
    #     hue="bench_name",
    # )

    # suite.generate_graph(
    #     title="Llcstat",
    #     plot_name="lineplot",
    #     x="nb_threads",
    #     y="llcstat_total_nr_misses",
    #     hue="bench_name",
    # )

    # suite.generate_graph(
    #     title="Strace",
    #     plot_name="lineplot",
    #     x="nb_threads",
    #     y="strace_total_time_s",
    #     hue="bench_name",
    # )

    suite.generate_graph(
        title="Thread Event Profile",
        plot_name="thread-profile",
        speedupstackwrapper=speedupstackwrapper,
        show_run_number=1,
    )

    # suite.generate_graph(
    #     plot_name="thread-profile",
    #     speedupstackwrapper=speedupstackwrapper,
    #     show_run_number=2,
    # )

    # suite.generate_graph(
    #     plot_name="thread-profile",
    #     speedupstackwrapper=speedupstackwrapper,
    #     show_run_number=3,
    # )

    # suite.generate_graph(
    #     plot_name="thread-profile",
    #     speedupstackwrapper=speedupstackwrapper,
    #     show_run_number=4,
    # )

    # suite.generate_graph(
    #     plot_name="thread-profile",
    #     speedupstackwrapper=speedupstackwrapper,
    #     show_run_number=5,
    # )

    suite.generate_graph(
        title="Speedup Stack",
        plot_name="speedup-stack",
        duration_transformation=time_transformation("s", "ns"),
        speedup_stack_components={
            "klockstat_total_wait_ns": _id,
            "offcputime_avg_micro_s": time_transformation("us", "ns"),
            "llcstat_total_nr_misses": _id,
            "strace_total_time_s": time_transformation("s", "ns"),
        },
        constant_duration=True,
        speed_metric="operations/second",
    )


def _id(val: float):
    return val


if __name__ == "__main__":
    main()
