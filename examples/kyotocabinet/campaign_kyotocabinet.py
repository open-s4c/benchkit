#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for Kyoto Cabinet benchmark.
"""

from kyotocabinet import kyotocabinet_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""
    kyotocabinet_src_dir = (get_curdir(__file__) / "deps/kyotocabinet-1.2.76/").resolve()

    campaign = kyotocabinet_campaign(
        src_dir=kyotocabinet_src_dir,
        nb_runs=1,
        benchmark_duration_seconds=3,
        nb_threads=[2, 4, 8],
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
