#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchmarks.cprogram import CProgramBench
from benchkit.campaign import CampaignIterateVariables
from benchkit.platforms import get_current_platform
from benchkit.commandattachments.tracecmd import TraceCmd


def main() -> None:
    platform = get_current_platform()

    traceCmd = TraceCmd(["sched"], platform)
    CampaignIterateVariables(
        name="attach",
        benchmark=CProgramBench(
            command_attachments=[traceCmd.attachment],
            post_run_hooks=[traceCmd.post_run_hook]
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
