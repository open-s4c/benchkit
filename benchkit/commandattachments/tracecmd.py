# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from typing import List
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType
from benchkit.platforms import get_current_platform, Platform
import pathlib


class TraceCmd:

    def __init__(self, events: List[str] = (), platform: Platform = None,) -> None:
        self.events = [str(e) for e in events]
        self.platform = platform if platform is not None else get_current_platform()
        self.pid = None
        
    def attachement(
        self,
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:

        rdd = pathlib.Path(record_data_dir)
        out_file = rdd / "trace.dat"

        self.pid = process.pid
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

    def post_run_hook(
        self,
        record_data_dir: PathType,
        **kwargs
        ) -> None:
        
        rdd = pathlib.Path(record_data_dir)
        print(rdd)
        
        command = ["trace-cmd", "report", "trace.dat"]
            
        AsyncProcess(
            platform=self.platform,
            arguments=command,
            stdout_path=rdd / "generate-graph.out",
            stderr_path=rdd / "generate-graph.err",
            current_dir=rdd,
        )
        