#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run tilt locks.
"""


# from tiltlib import SimpleMutexTestBench as Bench
from benchmark_lusearch import lusearch_campaign

from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.commandwrappers.perf import PerfStatWrap, enable_non_sudo_perf
from benchkit.utils.dir import caller_dir
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import get_curdir

# campaign_dir = caller_dir()
# tilt_locks_dir = campaign_dir / "locks"
# bench_src_dir = campaign_dir / "bench"
# vsync_dir = (tilt_locks_dir / "../deps/libvsync/").resolve()


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    # Define the "perf-stat" command wrapper to be passed to the benchmark initialization
    # It is used to collect information from the PMCs.
    # perfstatwrap = PerfStatWrap(events=["cache-misses"])
    perfstatwrap = PerfStatWrap(
            perf_path=None,
            events=[
                # "cache-misses",
                "context-switches"
                # "sched:sched_switch"
                ],
            use_json = False,
            separator=";",
            quiet=False,
            remove_absent_event=False,
            )

    # Where is the benchmark code located
    lusearch_src_dir = (get_curdir(__file__) / "deps/dacapobench/benchmarks/").resolve()

    # Define the campaign, associated with the LevelDB benchmark
    campaign = lusearch_campaign(
        src_dir=lusearch_src_dir,
        size=("small",),
        # size=("default",),
        bench_name=[
            "readrandom",
        ],
        nb_runs=1,
        benchmark_duration_seconds=3,
        nb_threads=[4, 2],
        command_wrappers=[perfstatwrap],
        post_run_hooks=[perfstatwrap.post_run_hook_update_results],
        enable_data_dir=True,
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate a graph to visualize the resulting throughputs
    suite.generate_graph(
        plot_name="barplot",
        x="nb_threads",
        y="duration",
    )

    # Generate a graph to visualize the output of perf stat
    suite.generate_graph(
        plot_name="barplot",
        x="nb_threads",
        y="perf-stat/context-switches",
    )

    # campaigns = [
    #     CampaignCartesianProduct(
    #         name="tilt",
    #         benchmark=Bench(
    #             src_dir=bench_src_dir,
    #             shared_libs=[tiltlib],
    #         ),
    #         nb_runs=1,
    #         variables={
    #             "lock": ["", "taslock", "caslock", "vcaslock-nolse", "vcaslock-lse"],
    #         },
    #         constants=None,
    #         debug=False,
    #         gdb=False,
    #         enable_data_dir=True,
    #         continuing=False,
    #     ),
    # ]
    # suite = CampaignSuite(campaigns=campaigns)
    # suite.print_durations()
    # suite.run_suite()


if __name__ == "__main__":
    main()
