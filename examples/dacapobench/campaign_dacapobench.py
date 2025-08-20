#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run benchmarks from dacapobench.
"""


from benchmark_dacapobench import dacapobench_campaign

from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import enable_non_sudo_perf
from benchkit.commandwrappers.speedupstack import SpeedupStackWrapper
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import caller_dir


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    # Where is the benchmark code located
    dacapobench_src_dir = (caller_dir() / "deps/dacapobench/benchmarks/").resolve()

    speedupstackwrapper = SpeedupStackWrapper()

    # Define the campaign, associated with the LevelDB benchmark
    campaign = dacapobench_campaign(
        src_dir=dacapobench_src_dir,
        size=("small",),
        # size=("default",),
        # size=("large",),
        bench_names=[
            # "avrora",
            # "batik",
            # "biojava",
            # "cassandra",
            # "eclipse",
            # "fop",
            # "graphchi",
            # "h2",
            # "jme",
            # "jython",
            # "kafka",
            # "luindex",
            # "lusearch",
            # "pmd",
            # "spring",
            # "sunflow",
            # "tomcat",
            # "tradebeans",
            # "tradesoap",
            "xalan",
            # "zxing",
            # "h2o", # Not supported due missing data
        ],
        nb_runs=1,
        benchmark_duration_seconds=3,
        nb_threads=[1, 2, 4, 8],
        command_wrappers=speedupstackwrapper.command_wrappers(),
        command_attachments=speedupstackwrapper.command_attachments(),
        post_run_hooks=speedupstackwrapper.post_run_hooks(),
        enable_data_dir=True,
        clean_in_between_different_benchmarks=False,
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_graph(
        plot_name="catplot",
        x="nb_threads",
        y="duration",
        col="bench_name",
        kind="bar",
    )

    # Generate a speedup stacks
    suite.generate_graph(
        plot_name="speedup-stack",
        use_json=True
    )


if __name__ == "__main__":
    main()
