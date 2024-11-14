#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from cgol_cpu import cgol_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


# Creates a campaign for a specific version of the code
def create_campaign_for_version(cgol_dir, version_nr):
    version_src_dir = cgol_dir / f"version-{version_nr}"
    campaign = cgol_campaign(
        src_dir=version_src_dir,
        build_dir=version_src_dir / "build",
        bench_name=["time_based"],
        nb_threads=[1, 2, 3, 4],
        size=[2000],
        benchmark_duration_seconds=25,
        nb_runs=30,
        constants={"bench_version": f"version-{version_nr}"},
    )
    return campaign


def main() -> None:
    """Main function of the campaign script."""

    # Root directory where the Conway's Game of Life implementation is located
    cgol_dir = (get_curdir(__file__).parent / "deps/conway-game-of-life-parallel/").resolve()

    # Define the campaign for the different CPU versions
    campaign_1 = create_campaign_for_version(cgol_dir, 1)
    campaign_2 = create_campaign_for_version(cgol_dir, 2)
    campaign_3 = create_campaign_for_version(cgol_dir, 3)
    campaign_4 = create_campaign_for_version(cgol_dir, 4)
    campaign_5 = create_campaign_for_version(cgol_dir, 5)
    campaign_6 = create_campaign_for_version(cgol_dir, 6)
    campaign_7 = create_campaign_for_version(cgol_dir, 7)

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign_1, campaign_2, campaign_3, campaign_4, campaign_5, campaign_6, campaign_7]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate a graph with the results
    suite.generate_graph(
        plot_name="barplot",
        x="nb_threads",
        y="throughput",
        xlabel="Number of threads",
        ylabel="Throughput (cells updated/sec)",
        hue="bench_version",
        title="Throughput vs. number of threads"
    )


if __name__ == "__main__":
    main()
