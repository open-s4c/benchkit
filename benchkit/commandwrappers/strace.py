# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `strace` utility that allows to trace all system calls used in the wrapped
command and output them into a file.
"""

import os
from os.path import exists
import pathlib
import re
import time
from typing import List, Optional

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import get_current_platform
from benchkit.platforms.generic import Platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType


class StraceWrap(CommandWrapper):
    """Command wrapper for the `strace` utility."""

    def __init__(
        self,
        pid: bool = False,
        summary: bool = True,
        summary_only: bool = False,
        trace_forks: bool = False,
        output_separately: bool = False,
        platform: Platform = None,
    ):
        super().__init__()

        self._pid = pid
        self._summary = summary
        self._summary_only = summary_only
        self._output_separately = output_separately
        self._trace_forks = trace_forks
        self.platform = platform if platform is not None else get_current_platform()

        self._output_file_name = "strace.txt"
        self.out_file_name = "strace.out"
        self.err_file_name = "strace.err"

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("strace"),
        ]

    def command_prefix(  # pylint: disable=arguments-differ
        self,
        record_data_dir: Optional[PathType],
        **kwargs,
    ) -> List[str]:
        cmd_prefix = super().command_prefix(**kwargs)

        if record_data_dir is None:
            raise ValueError(
                "Record data directory cannot be None, it is required to save strace output."
            )

        strace_output_pathname = os.path.join(record_data_dir, "strace.txt")

        options = []
        if self._summary:
            options.append("--summary")
        if self._summary_only:
            options.append("--summary-only")
        if self._output_separately:
            options.append("--output-separately")
        if self._trace_forks:
            options.append("--follow-forks")

        cmd_prefix = (
            ["strace"]
            + options
            + [
                "-o",
                f"{strace_output_pathname}",
            ]
            + cmd_prefix
        )

        return cmd_prefix

    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)
        strace_output_pathname = os.path.join(record_data_dir, self._output_file_name)

        command = ["strace", "-o", strace_output_pathname]

        if self._pid:
            command.extend(["-p", str(process.pid)])
        if self._summary:
            command.append("--summary")
        if self._summary_only:
            command.append("--summary-only")
        if self._output_separately:
            command.append("--output-separately")
        if self._trace_forks:
            command.append("--follow-forks")

        # Initialize AsyncProcess for strace
        self._process = AsyncProcess(
            platform=self.platform,
            arguments=command,
            stdout_path=rdd / self.out_file_name,
            stderr_path=rdd / self.err_file_name,
            current_dir=rdd,
        )

        # Wait until the clock stat has at least outputted something in the out file,
        # or the error file, in order to know that it has attached.
        while True:
            if ((os.path.getsize(rdd / self.out_file_name) > 0) or
                (os.path.getsize(rdd / self.err_file_name) > 0)):
                break
            time.sleep(0.05)


    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        self._process.send_signal(2, self._process.pid)
        self._process.wait()

        strace_output_file = os.path.join(record_data_dir, self._output_file_name)

        # This dictionary will hold all the values for each syscall
        per_syscall_dict = {}

        row_re = re.compile(r"^\s+(\d*.\d+)\s+(\d*.\d+)\s+(\d+)\s+(\d+)\s+(?:(\d+)\s+)?(\S+)$")

        with open(strace_output_file) as out_file:
            for line in out_file.readlines():
                line = line.rstrip()

                m = row_re.search(line)
                if m:
                    syscall_name = m.group(6)

                    per_syscall_dict[syscall_name] = {
                        "percentage_time": float(m.group(1)),
                        "time_s": float(m.group(2)),
                        "micro_s_per_call": int(m.group(3)),
                        "nr_calls": int(m.group(4)),
                        "nr_errors": int(m.group(5) if m.group(5) else 0),
                            }

        # __import__('pprint').pprint(per_syscall_dict)

        # Post run hooks must return a dictionary where each key at the top level corresponds
        # to some information to be kept. The current per-syscall dictionary
        # does not adhere to this structure.

        # TODO: Currently, the output from strace is processed by just taking a sum.
        # However, this is most likely not what the user wants when calling this post run hook.
        # For example, in the context of a locking benchmark, you might already be processing
        # the locks separately. So maybe we would like to be able to filter on certain system calls.
        total_time_s = sum(d["time_s"] for d in per_syscall_dict.values())
        return_dict = {
            "strace_total_time_s": total_time_s,
        }

        return return_dict
