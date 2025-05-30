# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `Xlog` functionality of the JVM.
"""

import os
from typing import List, Optional, Tuple

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.platforms import get_current_platform
from benchkit.sharedlibs import EnvironmentVariables
from benchkit.utils.types import Environment, PathType, SplitCommand

from . import CommandWrapper, PackageDependency


class JVMXlogWrap(CommandWrapper):
    """
Command wrapper for the `Xlog` functionality of the JVM.
    """

    def __init__(self) -> None:
        super().__init__()
        self.platform = get_current_platform()

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + []

    def wrap(
        self,
        command: SplitCommand,
        environment: Environment,
        record_data_dir: Optional[PathType] = None,
        **kwargs,
    ) -> Tuple[SplitCommand, EnvironmentVariables]:

        if record_data_dir is None:
            raise ValueError("Record data directory cannot be None, it is required to save the JVMXlog data.")
            
        jvmxlog_pathname = os.path.join(record_data_dir, "jvmxlog.log")
        cmd_infix = ["-XX:+ExtendedDTraceProbes", "-XX:+PreserveFramePointer", f'-Xlog:gc*:file="{jvmxlog_pathname}"']

        wrapped_command = [command[0]] + cmd_infix + command[1:]
        wrapped_environment = environment

        return wrapped_command, wrapped_environment

    def post_run_hook_update_results(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        """
        Post run hook to generate extension to record results dict with the captured JVMXlog values.
        """
        assert experiment_results_lines  # to remove the "unused" warning
        assert write_record_file_fun  # to remove the "unused" warning

        jvmxlog_pathname = os.path.join(record_data_dir, "jvmxlog.log")

        total_gc_time = 0
        with open(jvmxlog_pathname) as file:
            for line in file:
                splits = line.split(' ')
                if splits[0][-2:] == "gc":
                    gc_event = splits[splits.index(']') + 2:splits.index(']') + 4]
                    if len(gc_event) == 2 and gc_event[0] != "Concurrent" and gc_event[1] != "Remark" and gc_event[1] != "Cleanup":
                        timing = splits[-1].strip()[:-2]
                        try:
                            value = float(timing.replace(',', '.'))
                            total_gc_time += value
                        except ValueError:
                            pass

        output_dict = {'gc': total_gc_time}

        return output_dict
