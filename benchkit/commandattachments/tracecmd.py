# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType


class TraceCmd:

    def __init__(
        self,
        events: List[str] = (),
        platform: Platform = None,
    ) -> None:
        self._events = [str(e) for e in events]
        self._platform = platform if platform is not None else get_current_platform()
        self.pid = None
        self._process = None
        self._files_pid = []
        self._pre_run_hook = False
        
    def pre_run_hook(
        self,
        build_variables,
        run_variables,
        other_variables,
        record_data_dir,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)
        out_file = rdd / "trace.dat"


        
        command = ["sudo", "trace-cmd", "record", "-o", f"{out_file}"]   
        
         # Add "-e" and each event to the command list
        for event in self._events:
            command.extend(["-e", event])
        
        self._pre_run_hook = True
        
        self._process = AsyncProcess(
            platform=self._platform,
            arguments=command,
            stdout_path=rdd / "trace-cmd.out",
            stderr_path=rdd / "trace-cmd.err",
            current_dir=rdd,
        ) 
        
        
    """This attachment method should be used when starting trace-cmd with the pre_run_hook to get the pid of the running process"""    
    def attachment_with_pre_run_hook( 
        self,
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:
        self.pid = process.pid   
            
    def attachment(
        self,
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:

        rdd = pathlib.Path(record_data_dir)
        out_file = rdd / "trace.dat"

        self.pid = process.pid
        command = ["sudo", "trace-cmd", "record"]

        # Add "-e" and each event to the command list
        for event in self._events:
            command.extend(["-e", event])

        # Add the PID and output file arguments
        command.extend(["-P", f"{self.pid}", "-o", f"{out_file}"])

        self._process = AsyncProcess(
            platform=self._platform,
            arguments=command,
            stdout_path=rdd / "trace-cmd.out",
            stderr_path=rdd / "trace-cmd.err",
            current_dir=rdd,
        )

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> None:
        assert experiment_results_lines

        rdd = pathlib.Path(record_data_dir)
        print(rdd)

        if self._pre_run_hook:
            self._process.stop()
        else:    
            self._process.wait()

        command = ["trace-cmd", "report", "trace.dat"]

        output = self._platform.comm.shell(command=command, current_dir=rdd, print_output=False)
        write_record_file_fun(output, "generate-graph.out")
        self._files_pid.append((rdd / "generate-graph.out", self.pid))
