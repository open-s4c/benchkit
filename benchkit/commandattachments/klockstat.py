# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
from threading import Thread
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shellasync import AsyncProcess, shell_async
from benchkit.utils.types import PathType


class Klockstat:

    """
    Klockstat is an libbpf-tools util that monitors locks.
    NOTE: the klockstat utility requires added capabilities so that it
          can run with root privileges without sudo.
        
    Arguments:
        sort_by_field: acq_[max|total|count] or hld_[max|total|count]
    """

    def __init__(
        self,
        libbpf_tools_dir: PathType,
        pid: bool = True,
        tid: int = -1,
        caller_string_prefix: str = "",
        lock_ksys_name_filter: str = "",
        max_nr_locks_or_threads: int = -1,
        max_nr_stack_entries: int = -1, 
        sort_by_field: str = "",
        duration: int = -1,
        interval: int = -1,
        print_per_thread: bool = False,
        reset_stats_each_interval: bool = False, 
        print_time_stamp: bool = False,

        platform: Platform = None,
    ) -> None:

        if libbpf_tools_dir == "":
            raise ValueError("The provided libbpf_tools_dir is empty")

        self._libbpf_tools_dir = libbpf_tools_dir
        self._pid = pid
        self._tid = tid
        self._caller_string_prefix = caller_string_prefix
        self._lock_ksys_name_filter = lock_ksys_name_filter
        self._max_nr_locks_or_threads = max_nr_locks_or_threads
        self._max_nr_stack_entries = max_nr_stack_entries
        self._sort_by_field = sort_by_field
        self._duration = duration
        self._interval = interval
        self._print_per_thread = print_per_thread
        self._reset_stats_each_interval = reset_stats_each_interval
        self._print_time_stamp = print_time_stamp

        self.process = (None,)
        self.platform = platform if platform is not None else get_current_platform()

    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)

        lib_path = pathlib.Path(self._libbpf_tools_dir).as_posix()

        # command = ["sudo", lib_path + "/klockstat"]
        command = [lib_path + "/klockstat"]

        if self._pid:
            command.extend(["-p", str(process.pid)])

        if self._tid > 0:
            command.extend(["-t", str(self._tid)])

        if self._caller_string_prefix:
            command.extend(["-c", self._caller_string_prefix])

        if self._lock_ksys_name_filter:
            command.extend(["-L", self._lock_ksys_name_filter])

        if self._max_nr_locks_or_threads > 0:
            command.extend(["-n", str(self._max_nr_locks_or_threads)])

        if self._max_nr_stack_entries > 0:
            command.extend(["-s", str(self._max_nr_stack_entries)])

        if self._sort_by_field:
            command.extend(["-S", self._sort_by_field])

        if self._duration > 0:
            command.extend(["-d", str(self._duration)])

        if self._interval > 0:
            command.extend(["-i", str(self._interval)])

        if self._print_per_thread:
            command.append("-P")

        if self._reset_stats_each_interval:
            command.append("-R")

        if self._print_time_stamp:
            command.append("-T")

        # Initialize AsyncProcess for klockstat
        self._process = AsyncProcess(
            platform=self.platform,
            arguments=command,
            stdout_path=rdd / "klockstat.out",
            stderr_path=rdd / "klockstat.err",
            current_dir=rdd,
        )

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> None:
        print("waiting #################################################: " )
        self._process.send_signal(2, self._process.pid)
        self._process.wait()
        print("done #################################################: ")
