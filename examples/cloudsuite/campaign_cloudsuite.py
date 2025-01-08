#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for cloud suite benchmark.
"""

from cloudsuite import cloudsuite_campaign

from benchkit.campaign import CampaignSuite
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import caller_dir


def main() -> None:
    platform = get_current_platform()

    deps_dir = (caller_dir() / "deps").resolve()
    cloudsuite_src_dir = deps_dir / "cloudsuite"

    campaign = cloudsuite_campaign(
        name="cloudsuite",
        benchmark=None,
        src_dir=cloudsuite_src_dir,
        server_platform=platform,
        web_server_platform=platform,
        platform=platform,
        nb_runs=1,
        benchmark_duration_seconds=30,
        nb_threads=[1, 3],
        generator_seeds=[0],
        enable_data_dir=True,
        continuing=False,
        constants=None,
        pretty=None,
    )

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
    )


if __name__ == "__main__":
    main()
