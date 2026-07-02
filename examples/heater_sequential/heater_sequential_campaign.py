#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.benches.heater import heater_seq_campaign
from benchkit.campaign import CampaignSuite
from benchkit.platforms import get_current_platform


def main() -> None:
    """Main function of the campaign script."""

    # Define the platform where to run the benchmark
    platform = get_current_platform()

    # Define the campaign
    campaign = heater_seq_campaign(
        nb_runs=1,
        duration_s=1,
        cpu=range(0, platform.nb_cpus()),
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate a graph to visualize the results
    suite.generate_graph(
        plot_name="barplot",
        x="cpu",
        y="ops",
        title=f"Sequential Heater on {get_current_platform().comm.hostname()}",
    )


if __name__ == "__main__":
    main()
