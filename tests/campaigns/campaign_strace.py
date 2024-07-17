#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.commandwrappers.strace import StraceWrap
from benchkit.campaign import CampaignIterateVariables
from benchmarks.sleep import SleepBench


def main() -> None:
    CampaignIterateVariables(
        name="strace",
        benchmark=SleepBench(command_wrappers=[StraceWrap()]),
        nb_runs=1,
        variables=[
            {
                "duration_seconds": 1,
            },
        ],
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
    ).run()


if __name__ == '__main__':
    main()
