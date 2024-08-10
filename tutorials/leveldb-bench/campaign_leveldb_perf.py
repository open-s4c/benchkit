#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for LevelDB benchmarks, showcasing how `perf` can be used to gather
information from the Performance Monitoring Counters (PMCs).
"""

from leveldb import leveldb_campaign

from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import PerfStatWrap, enable_non_sudo_perf
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    # Where is the benchmark code located
    leveldb_src_dir = (get_curdir(__file__) / "deps/leveldb/").resolve()

    # Define the "perf-stat" command wrapper to be passed to the benchmark initialization
    # It is used to collect information from the PMCs.
    perfstatwrap = PerfStatWrap(events=["cache-misses"], separator=";")

    # Define the campaign, associated with the LevelDB benchmark
    campaign = leveldb_campaign(
        src_dir=leveldb_src_dir,
        bench_name=[
            "readrandom",
        ],
        nb_runs=1,
        benchmark_duration_seconds=3,
        nb_threads=[2, 4],
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
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="bench_name",
    )

    # Generate a graph to visualize the output of perf stat
    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="perf-stat/cache-misses",
        hue="bench_name",
    )


if __name__ == "__main__":
    main()
