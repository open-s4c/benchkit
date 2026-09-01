# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `Xlog` functionality of the JVM.
"""

import os
import re
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
        self._nb_threads = 1

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
            raise ValueError(
                "Record data directory cannot be None, it is required to save the JVMXlog data."
            )

        jvmxlog_pathname = os.path.join(record_data_dir, "jvmxlog.log")
        cmd_infix = [
            "-XX:+ExtendedDTraceProbes",
            "-XX:+PreserveFramePointer",
            f'-Xlog:gc*:file="{jvmxlog_pathname}"',
        ]

        wrapped_command = [command[0]] + cmd_infix + command[1:]
        wrapped_environment = environment

        return wrapped_command, wrapped_environment

    def prerun_hook(
        self,
        build_variables: RecordResult,
        run_variables: RecordResult,
        other_variables: RecordResult,
        record_data_dir: PathType,
    ) -> None:
        if "nb_threads" not in run_variables:
            print("ERROR: JVMXlogWrap expects the 'nb_threads' variable to be present")
            return

        self._nb_threads = run_variables["nb_threads"]

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

        pause_ms_re = re.compile(r"(\d+(?:[.,]\d+)?)ms$")

        total_gc_time: float = 0
        with open(jvmxlog_pathname) as file:
            for line in file:
                if " GC(" in line and " Pause " in line:
                    m = pause_ms_re.search(line)
                    if m:
                        total_gc_time += float(m.group(1).replace(",", "."))

        output_dict = {"jvmxlogwrap_gc_ms": total_gc_time * self._nb_threads}

        return output_dict
