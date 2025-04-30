#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run benchmarks from dacapobench.
"""


from benchmark_dacapobench import dacapobench_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


def main() -> None:

    # Where is the benchmark code located
    dacapobench_src_dir = (get_curdir(__file__) / "deps/dacapobench/benchmarks/").resolve()

    # Define the campaign, associated with the LevelDB benchmark
    campaign = dacapobench_campaign(
        src_dir=dacapobench_src_dir,
        size=("small",),
        # size=("default",),
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
            "zxing",

            # "h2o", # Not supported due missing data

        ],
        nb_runs=5,
        benchmark_duration_seconds=3,
        nb_threads=[1, 2, 4],
        enable_data_dir=True,
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate a graph to visualize the resulting throughputs
    # suite.generate_graph(
    #     plot_name="barplot",
    #     x="nb_threads",
    #     y="duration",
    #     hue="bench_name",
    # )

    suite.generate_graph(
        plot_name="catplot",
        x="nb_threads",
        y="duration",
        col="bench_name",
        kind="bar",
    )


if __name__ == "__main__":
    main()
