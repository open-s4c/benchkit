# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
This module implements an attachment that will output the off-CPU time of the monitoring process.
An example use case of this attachment is to monitor the load imbalance of the benchmark.

The documentation for the Python binding of this tool can be found here.
Note that we are not using the Python binding
but the core information still remains relevant.
    https://man.docs.euro-linux.com/EL%209/bcc-tools/bcc-offcputime.8.en.html
"""

import os
import pathlib
import re
import time
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandattachments.libbpftools import LibbpfTools
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType


class Offcputime(LibbpfTools):
    """
    Offcputime is a libbpf-tools util that monitors off CPU time.
    NOTE: the offcputime utility requires added capabilities so that it
          can run with root privileges without sudo.

    Arguments:
        libbpf_tools_dir: the directory that points to the libbpf tools
        pid: Trace these PIDs only (True = trace the current process)
        tid: Trace these TIDs only (the given tid is used for tracing)
        kernel_threads_only: Kernel threads only (no user threads)
        user_threads_only: User threads only (no kernel threads)
        min_block_time: the amount of time in microseconds over which we store traces
                        (default 1)
        max_block_time: the amount of time in microseconds under which we store traces
                        (default U64_MAX)
        perf_max_stack_depth: the limit for both kernel and user stack traces
                        (default 127)
        stack_storage_size: the number of unique stack traces that can be stored and displayed
                        (default 1024)
        state: filter on this thread state bitmask (eg, 2 == TASK_UNINTERRUPTIBLE)
                        see include/linux/sched.h
    """

    def __init__(
        self,
        libbpf_tools_dir: PathType,
        pid: bool = True,
        tid: int = -1,  # TODO: support list of tids?
        kernel_threads_only: bool = False,
        user_threads_only: bool = False,
        min_block_time: int = -1,
        max_block_time: int = -1,
        perf_max_stack_depth: int = -1,
        stack_storage_size: int = -1,
        state: int = -1,
        platform: Platform = None,
    ) -> None:

        self.platform = platform if platform is not None else get_current_platform()

        if not self.platform.comm.path_exists(libbpf_tools_dir):
            raise ValueError("The provided libbpf_tools_dir does not exist")

        self._libbpf_tools_dir = libbpf_tools_dir
        self._pid = pid
        self._tid = tid
        self._kernel_threads_only = kernel_threads_only
        self._user_threads_only = user_threads_only
        self._min_block_time = min_block_time
        self._max_block_time = max_block_time
        self._perf_max_stack_depth = perf_max_stack_depth
        self._stack_storage_size = stack_storage_size
        self._state = state

        self.out_file_name = "offcputime.out"
        self.err_file_name = "offcputime.err"

    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)

        lib_path = pathlib.Path(self._libbpf_tools_dir).as_posix()

        command = [lib_path + "/offcputime"]

        if self._pid:
            command.extend(["-p", str(process.pid)])

        if self._tid > 0:
            command.extend(["-t", str(self._tid)])

        if self._kernel_threads_only:
            command.append("-k")

        if self._user_threads_only:
            command.append("-u")

        if self._min_block_time > 0:
            command.extend(["-m", str(self._min_block_time)])

        if self._max_block_time > 0:
            command.extend(["-M", str(self._max_block_time)])

        if self._perf_max_stack_depth > 0:
            command.append("--perf-max-stack-depth=" + str(self._perf_max_stack_depth))

        if self._stack_storage_size > 0:
            command.append("--stack-storage-size=" + str(self._stack_storage_size))

        if self._state > 0:
            command.append("--state=" + str(self._state))

        # Initialize AsyncProcess for offcputime
        self._process = AsyncProcess(
            platform=self.platform,
            arguments=command,
            stdout_path=rdd / self.out_file_name,
            stderr_path=rdd / self.err_file_name,
            current_dir=rdd,
        )

        # Wait until offcputime has at least outputted something in the out file,
        # or the error file, in order to know that it has attached the eBPF.
        for _ in range(100):
            if (self.platform.comm.file_size(rdd / self.out_file_name) > 0) or (
                self.platform.comm.file_size(rdd / self.err_file_name) > 0
            ):
                break
            time.sleep(0.05)
        else:
            raise TimeoutError("Offcputime attachment was not able to attach")

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        self._process.send_signal(2, self._process.pid)
        self._process.wait()

        rdd = pathlib.Path(record_data_dir)
        offcputime_out_file = rdd / self.out_file_name
        offcputime_err_file = rdd / self.err_file_name

        # if the error file is not empty print the content of the error file
        # and return an empty dictionary
        if os.stat(offcputime_err_file).st_size != 0:
            with open(offcputime_err_file) as err_file:
                for line in err_file.readlines():
                    print(line)
                return {}

        # This dictionary will hold all the aggregated values for each pid
        per_pid_dict = {}

        row_re = re.compile(r"^\((\S+)\)\s+(\d+)\s+(\d+)$")

        with open(offcputime_out_file) as out_file:
            for line in out_file.readlines():
                line = line.rstrip()

                m = row_re.search(line)
                if m:
                    name = m.group(1)
                    pid = int(m.group(2))
                    delta_micro_s = int(m.group(3))

                    old_values = per_pid_dict.setdefault(
                        pid,
                        {
                            "name": name,
                            "total_off_time_micro_s": 0,
                        },
                    )

                    per_pid_dict[pid].update(
                        {
                            "total_off_time_micro_s": old_values["total_off_time_micro_s"]
                            + delta_micro_s,
                        }
                    )

        number_of_pids = len(per_pid_dict.keys())
        return_dict = {
            "avg_offcputime_micro_s": (
                (sum(d["total_off_time_micro_s"] for d in per_pid_dict.values()) / number_of_pids)
                if number_of_pids != 0
                else 0
            )
        }
        return return_dict
