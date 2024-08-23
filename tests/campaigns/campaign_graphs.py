#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT


from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.platforms import get_current_platform
from tests.campaigns.benchmarks.sleep import SleepBench
from pandas import DataFrame


def add_ms(dataframe: DataFrame) -> DataFrame:
    dataframe["duration_ms"] = dataframe["duration_seconds"] / 1000.0
    return dataframe


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
    campaign.generate_graph(
        plot_name="barplot",
        process_dataframe=add_ms,
        x="duration_ms",
        y="duration_ms",
    )

    campaign_suite = CampaignSuite(campaigns=[campaign])
    campaign_suite.generate_global_csv()
    campaign_suite.generate_graph(
        plot_name="lineplot",
        process_dataframe=add_ms,
        x="duration_ms",
        y="duration_ms",
        hue="rep",
        markers=True,
        dashes=False,
    )


if __name__ == "__main__":
    main()
