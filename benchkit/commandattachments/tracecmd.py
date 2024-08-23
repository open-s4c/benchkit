# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from typing import List
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType
from benchkit.platforms import get_current_platform, Platform
import pathlib


class TraceCmd:

    def __init__(self, events: List[str] = (), platform: Platform = None):
        self.events = [str(e) for e in events]
        self.platform = platform
    def attachement(
        self,
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:
        if self.platform == None:
            get_current_platform()

        rdd = pathlib.Path(record_data_dir)
        out_file = rdd / "trace.dat"

        pid = process.pid
        command = ["sudo", "trace-cmd", "record"]

        # Add "-e" and each event to the command list
        for event in self.events:
            command.extend(["-e", event])

        # Add the PID and output file arguments
        command.extend(["-P", f"{pid}", "-o", f"{out_file}"])

        AsyncProcess(
            platform=self.platform,
            arguments=command,
            stdout_path=rdd / "trace-cmd.out",
            stderr_path=rdd / "trace-cmd.err",
            current_dir=rdd,
        )
