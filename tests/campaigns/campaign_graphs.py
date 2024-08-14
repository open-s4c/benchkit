#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.campaign import CampaignCartesianProduct
from benchkit.platforms import get_current_platform
from tests.campaigns.benchmarks.sleep import SleepBench


def main() -> None:
    platform = get_current_platform()

    campaign = CampaignCartesianProduct(
        name="charts",
        benchmark=SleepBench(platform=platform),
        nb_runs=2,
        variables={"duration_seconds": [1, 2]},
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
    )
    campaign.run()
    campaign.generate_graph(
        plot_name="lineplot",
        x="duration_seconds",
        y="duration_seconds",
        hue="rep",
        markers=True,
        dashes=False,
    )
    campaign.generate_graph(
        plot_name="barplot",
        x="duration_seconds",
        y="duration_seconds",
    )


if __name__ == "__main__":
    main()
