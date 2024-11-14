#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from cgol_cpu import cgol_campaign

from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import PerfStatWrap
from benchkit.utils.dir import get_curdir


# Creates a campaign for a specific version of the code
def create_campaign_for_version(cgol_dir, version_nr):
    version_src_dir = cgol_dir / f"version-{version_nr}"
    wrapper = PerfStatWrap(
        events=["instructions", "cache-misses", "cache-references"],
    )

    campaign = cgol_campaign(
        command_wrappers=[wrapper],
        post_run_hooks=[wrapper.post_run_hook_update_results],
        src_dir=version_src_dir,
        build_dir=version_src_dir / "build",
        bench_name=["generation_based"],
        nb_threads=[4],
        size=[5000],
        nb_generations=[30],
        nb_runs=30,
        enable_data_dir=True,
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

    # Generate graphs with the results
    suite.generate_graph(
        plot_name="barplot",
        x="bench_version",
        y="perf-stat/instructions",
        xlabel="Implementation",
        ylabel="Instructions",
        hue="bench_version",
        title="Instructions executed per implementation",
    )

    suite.generate_graph(
        plot_name="barplot",
        x="bench_version",
        y="perf-stat/cache-misses",
        xlabel="Implementation",
        ylabel="Cache misses",
        hue="bench_version",
        title="Cache misses per implementation",
    )

    suite.generate_graph(
        plot_name="barplot",
        x="bench_version",
        y="perf-stat/cache-references",
        xlabel="Implementation",
        ylabel="Cache references",
        hue="bench_version",
        title="Cache references per implementation",
    )


if __name__ == "__main__":
    main()
