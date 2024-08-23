#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchmarks.cprogram import CProgramBench
from benchkit.campaign import CampaignIterateVariables
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType
from benchkit.platforms import get_current_platform
from benchkit.commandattachments.tracecmd import TraceCmd
import pathlib


def main() -> None:
    platform = get_current_platform()

    CampaignIterateVariables(
        name="attach",
        benchmark=CProgramBench(
            command_attachments=[
                TraceCmd(["sched"]).attachement
            ],
        ),
        nb_runs=1,
        variables=[{}],
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
    ).run()


if __name__ == "__main__":
    main()