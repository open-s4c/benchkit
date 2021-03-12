#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for micro-benchmarking the VSync locks.
"""

from vsyncmicrobench import LockMicroBench

from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.shell.shell import shell_out

NB_RUNS = 3
LOCKS = ["cas", "ttas", "ticket"]
DURATION_SECONDS = 3


def main() -> None:
    """Main function of the campaign script."""
    kernel = shell_out("uname -r").strip()
    campaign = CampaignCartesianProduct(
        name="mylockcampaign",
        benchmark=LockMicroBench(),
        nb_runs=NB_RUNS,
        variables={
            "lock": LOCKS,
            "nb_threads": [2, 4, 8],
        },
        constants={
            "kernel": kernel,
        },
        debug=False,
        gdb=False,
        enable_data_dir=False,
        benchmark_duration_seconds=DURATION_SECONDS,
        pretty={
            "lock": {
                "cas": "CAS spinlock",
                "ttas": "TTAS lock",
                "ticket": "Ticketlock",
            }
        },
    )

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="global_count",
        hue="lock",
    )


if __name__ == "__main__":
    main()
