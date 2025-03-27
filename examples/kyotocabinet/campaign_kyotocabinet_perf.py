#!/usr/bin/env python3
# Copyright (C) 2025 lelele group. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for Kyoto Cabinet benchmarks, showcasing how `perf` can be used to gather
information from the Performance Monitoring Counters (PMCs).
"""

from kyotocabinet import kyotocabinet_campaign

from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import PerfStatWrap, enable_non_sudo_perf
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    # Where is the benchmark code located
    kyotocabinet_src_dir = (get_curdir(__file__) / "deps/kyotocabinet-1.2.76/").resolve()

    # Define the "perf-stat" command wrapper to be passed to the benchmark initialization
    # It is used to collect information from the PMCs.
    perfstatwrap = PerfStatWrap(events=["cache-misses"])

    # Define the campaign, associated with the Kyoto Cabinet benchmark
    campaign = kyotocabinet_campaign(
        src_dir=kyotocabinet_src_dir,
        test_name=[],
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
        hue="test_name",
    )

    # Generate a graph to visualize the output of perf stat
    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="perf-stat/cache-misses",
        hue="test_name",
    )


if __name__ == "__main__":
    main()

