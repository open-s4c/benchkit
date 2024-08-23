#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchmarks.cprogram import CProgramBench
from benchkit.campaign import CampaignIterateVariables
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType
from benchkit.platforms import get_current_platform
import pathlib


def main() -> None:
    platform = get_current_platform()

    def perf_attach(
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)

        pid = process.pid
        command = ["perf", "record", "-p", f"{pid}"]

        AsyncProcess(
            platform=platform,
            arguments=command,
            stdout_path=rdd / "perf.out",
            stderr_path=rdd / "perf.err",
            current_dir=rdd,
        )

    CampaignIterateVariables(
        name="attach",
        benchmark=CProgramBench(
            command_attachments=[
                perf_attach
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
