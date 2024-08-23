# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType
from benchkit.platforms import get_current_platform
import pathlib

class trace_cmd_attachement():

    def __init__(
        self,
        events: list[str] = []
    ):
        self.events = events

    def attachement(
                self,
                process: AsyncProcess,
                record_data_dir: PathType,
        ) -> None:
            platform = get_current_platform()

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
                platform=platform,
                arguments=command,
                stdout_path=rdd / "trace-cmd.out",
                stderr_path=rdd / "trace-cmd.err",
                current_dir=rdd,
            )