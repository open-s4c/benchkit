#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.campaign import CampaignIterateVariables, CampaignSuite
from benchmarks.truefalse import TrueFalseBench


def main() -> None:
    CampaignIterateVariables(
        name="simple",
        benchmark=TrueFalseBench(),
        nb_runs=1,
        variables=[
            {
                "run_false": False,
            },
            {
                "run_false": True,
            },
        ],
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
    ).run()


if __name__ == "__main__":
    main()
