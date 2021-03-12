#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for Will-it-Scale benchmark.
"""

from willitscale import willitscale_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""
    willitscale_src_dir = (get_curdir(__file__) / "deps/will-it-scale/").resolve()

    campaign = willitscale_campaign(
        src_dir=willitscale_src_dir,
        nb_runs=1,
        benchmark_duration_seconds=3,
        test_name=["lock1_processes"],
        warmup_iterations=[2],
        nb_threads=[2, 4, 8],
    )

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
