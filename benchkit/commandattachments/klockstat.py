# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Klockstat is an attachment that will monitor the kernel locking events of the monitored process.
The collected data includes lock waiting times, which indicate how long the process waits for
a lock to become available, and lock hold time.
These are the actual times that processes have the locks.

Documentation of the underlying tool:
    https://man.docs.euro-linux.com/EL%209/bcc-tools/bcc-klockstat.8.en.html
"""

import os
from os.path import exists
import pathlib
import re
import time
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandattachments.libbpftools import LibbpfTools
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType


class Klockstat(LibbpfTools):
    """
    Klockstat is a libbpf-tools util that monitors locks.
    NOTE: the klockstat utility requires added capabilities so that it
          can run with root privileges without sudo.

    Arguments:
        libbpf_tools_dir: the directory that points to the libbpf tools
        pid: Filter by process ID (True = use the process PID)
        tid: Filter by thread ID (the given tid is used for filtering)
        caller_string_prefix: Filter by caller string prefix
        lock_ksys_name_filter: Filter by specific ksym lock name
        max_nr_locks_or_threads: Number of locks or threads to print
        max_nr_stack_entries: Number of stack entries to print per lock
        sort_by_field: Sort by field, values like -> acq_[max|total|count] or hld_[max|total|count]
        duration: Duration to trace
        interval: Print interval
        print_per_thread: Print per-thread stats
        reset_stats_each_interval: Reset stats each interval
        print_time_stamp: Print timestamp
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

        self.platform = platform if platform is not None else get_current_platform()

        if not self.platform.comm.path_exists(libbpf_tools_dir):
            raise ValueError("The provided libbpf_tools_dir does not exist")

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

        self.out_file_name = "klockstat.out"
        self.err_file_name = "klockstat.err"

        self.out_file_name = "klockstat.out"
        self.err_file_name = "klockstat.err"

    def attachment(
        self,
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)

        lib_path = pathlib.Path(self._libbpf_tools_dir).as_posix()

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
            stdout_path=rdd / self.out_file_name,
            stderr_path=rdd / self.err_file_name,
            current_dir=rdd,
        )

        # Wait until klockstat has at least outputted something in the out file,
        # or the error file, in order to know that it has attached the eBPF.
        for _ in range(100):
            if (self.platform.comm.file_size(rdd / self.out_file_name) > 0) or (
                self.platform.comm.file_size(rdd / self.err_file_name) > 0
            ):
                break
            time.sleep(0.05)
        else:
            raise TimeoutError("Klockstat attachment was not able to attach")

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        self._process.send_signal(2, self._process.pid)
        self._process.wait()

        rdd = pathlib.Path(record_data_dir)
        klockstat_out_file = rdd / self.out_file_name
        klockstat_err_file = rdd / self.err_file_name

        # if the error file is not empty print the content of the error file
        # and return an empty dictionary
        if os.stat(klockstat_err_file).st_size != 0:
            with open(klockstat_err_file) as err_file:
                for line in err_file.readlines():
                    print(line)
                return {}

        # This dictionary will hold all the aggregated values for each lock
        per_lock_dict = {}

        time_regex = re.compile(r"^\s*(\d+\.?\d*)\s*(ns|us|ms|s|m|h)\s*$", re.IGNORECASE)

        def parse_time_to_ns(s: str) -> float:
            """Parse strings like '1.6 us', '800 ns', '2.3 ms' -> nanoseconds (float)."""
            m = time_regex.match(s.rstrip())
            if not m:
                raise ValueError(f"can't parse time value: {s}")
            val = float(m.group(1))
            unit = m.group(2).lower()
            return (
                val
                * {"ns": 1.0, "us": 1e3, "ms": 1e6, "s": 1e9, "m": 1e9 * 60, "h": 1e9 * 3600}[unit]
            )

        current_table = "wait"
        row_re = re.compile(r"(\S+)\s+(\S+\s+\S+)\s+(\d+)\s+(\S+\s+\S+)\s+(\S+\s+\S+)")

        with open(klockstat_out_file) as out_file:
            for line in out_file.readlines():
                line = line.rstrip()

                if "Avg Wait" in line:
                    current_table = "wait"
                    continue
                if "Avg Hold" in line:
                    current_table = "hold"
                    continue

                m = row_re.search(line)
                if m:
                    caller = m.group(1)
                    avg_key = "avg_" + current_table
                    count_key = "count_" + current_table
                    max_key = "max_" + current_table
                    total_key = "total_" + current_table

                    parsed_avg = parse_time_to_ns(m.group(2))
                    parsed_count = int(m.group(3))
                    parsed_max = parse_time_to_ns(m.group(4))
                    parsed_total = parse_time_to_ns(m.group(5))

                    old_values = per_lock_dict.setdefault(
                        caller,
                        {
                            "avg_wait": 0,
                            "count_wait": 0,
                            "max_wait": 0,
                            "total_wait": 0,
                            "avg_hold": 0,
                            "count_hold": 0,
                            "max_hold": 0,
                            "total_hold": 0,
                        },
                    )

                    per_lock_dict[caller].update(
                        {
                            avg_key: (
                                old_values[avg_key] * old_values[count_key]
                                + parsed_avg * parsed_count
                            )
                            / (old_values[count_key] + parsed_count),
                            count_key: old_values[count_key] + parsed_count,
                            max_key: max(old_values[max_key], parsed_max),
                            total_key: old_values[total_key] + parsed_total,
                        }
                    )

            # Post run hooks must return a dictionary where each key at the top level corresponds
            # to some information to be kept. The current per-lock dictionary
            # does not adhere to this structure.

            total_wait = sum(d["total_wait"] for d in per_lock_dict.values())
            total_hold = sum(d["total_hold"] for d in per_lock_dict.values())
            count_wait = sum(d["count_wait"] for d in per_lock_dict.values())
            count_hold = sum(d["count_wait"] for d in per_lock_dict.values())
            return_dict = {
                "klockstat_total_wait_ns": total_wait,
                "klockstat_avg_wait_ns": (total_wait / count_wait) if count_wait != 0 else 0,
                "klockstat_max_wait_ns": max(
                    list(d["max_wait"] for d in per_lock_dict.values()) + [0]
                ),
                "klokstat_total_hold_ns": total_hold,
                "klockstat_avg_hold_ns": (total_hold / count_hold) if count_hold != 0 else 0,
                "klockstat_max_hold_ns": max(
                    list(d["max_hold"] for d in per_lock_dict.values()) + [0]
                ),
            }

            return return_dict
