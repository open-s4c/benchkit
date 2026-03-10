# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
TODO
"""

import os
import pathlib
import re
from collections import defaultdict
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandattachments import wait_for_output
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType


class ThreadProfiler:
    """
    ThreadProfiler is a eBPF tool that profiles threads using events.

    Arguments:
        thread_profiler_dir: the directory that points to threadprofiler
        pid: Filter by process ID (True = use the process PID)
        tid: Filter by thread ID (the given tid is used for filtering)
        granularity: Size of granularity for profile blocks in ns
    """

    def __init__(
        self,
        thread_profiler_dir: PathType,
        pid: bool = True,
        tid: int = -1,
        granularity: int = -1,
        platform: Platform = None,
    ) -> None:

        self.platform = platform if platform is not None else get_current_platform()

        if not self.platform.comm.path_exists(thread_profiler_dir):
            raise ValueError("The provided thread_profiler_dir does not exist")

        self._thread_profiler_dir = thread_profiler_dir
        self._pid = pid
        self._tid = tid
        self._granularity_ns = granularity
        self._per_run_per_thread_profile = {}
        self._run_counter = 1

        self.out_file_name = "threadprofiler.out"
        self.err_file_name = "threadprofiler.err"

    def attachment(
        self,
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)

        lib_path = pathlib.Path(self._thread_profiler_dir).as_posix()

        command = [lib_path + "/thread-profiler"]

        if self._pid:
            command.extend(["-p", str(process.pid)])

        if self._tid > 0:
            command.extend(["-t", str(self._tid)])

        if self._granularity_ns > 0:
            command.extend(["-g", str(self._granularity_ns)])

        # Initialize AsyncProcess for threadprofiler
        self._process = AsyncProcess(
            platform=self.platform,
            arguments=command,
            stdout_path=rdd / self.out_file_name,
            stderr_path=rdd / self.err_file_name,
            current_dir=rdd,
        )

        # Wait until klockstat has at least outputted something in the out file,
        # or the error file, in order to know that it has attached the eBPF.
        wait_for_output([rdd / self.out_file_name, rdd / self.err_file_name], self.platform)

    def attachment_thread(self, command: list[str]):
        self.platform.comm.shell(command=command)

    def get_per_thread_profiles(self):
        return self._per_run_per_thread_profile

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        self._process.send_signal(2, self._process.pid)
        self._process.wait()

        rdd = pathlib.Path(record_data_dir)
        threadprofiler_out_file = rdd / self.out_file_name
        threadprofiler_err_file = rdd / self.err_file_name

        # if the error file is not empty print the content of the error file
        # and return an empty dictionary
        if os.stat(threadprofiler_err_file).st_size != 0:
            with open(threadprofiler_err_file) as err_file:
                for line in err_file.readlines():
                    print(line)
                return {}

        # This dictionary will hold all the aggregated values for each lock
        per_thread_dict: dict[int, list] = defaultdict(list)
        row_re = re.compile(
            r"^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s*(\d+)?\s*$"
        )

        with open(threadprofiler_out_file) as out_file:
            for line in out_file.readlines():
                line = line.rstrip()

                m = row_re.search(line)
                if m:
                    tid = int(m.group(1))
                    block_index = int(m.group(2))
                    block_start_time_ns = int(m.group(3))
                    first_event_time_ns = int(m.group(4))
                    last_event_time_ns = int(m.group(5))
                    offcpu_time_ns = int(m.group(6))
                    mutex_wait_time_ns = int(m.group(7))
                    disk_io_time_ns = int(m.group(8))
                    end_state = m.group(9)
                    cutoff_time_ns = int(m.group(10)) if m.group(10) else None

                    # print(
                    #     tid,
                    #     block_index,
                    #     block_start_time_ns,
                    #     first_event_time_ns,
                    #     last_event_time_ns,
                    #     offcpu_time_ns,
                    #     end_state,
                    # )

                    # TODO: maybe filter out if block id 0 after end (Main thread?)

                    if tid in per_thread_dict:
                        # If you are not the first block make sure to grow
                        # the previous one until yourself
                        per_thread_dict[tid][-1][
                            "block_end_time_ns"
                        ] = block_start_time_ns  # TODO: Maybe +1

                        # If a block that is not the first has the id 0 then it should be ignored
                        if block_index == 0:
                            continue

                    per_thread_dict[tid].append(
                        {
                            "block_index": block_index,
                            "block_start_time_ns": block_start_time_ns,
                            "first_event_time_ns": first_event_time_ns,
                            "last_event_time_ns": last_event_time_ns,
                            "offcpu_time_ns": offcpu_time_ns,
                            "mutex_wait_time_ns": mutex_wait_time_ns,
                            "disk_io_time_ns": disk_io_time_ns,
                            "end_state": end_state,
                            "cutoff_time_ns": cutoff_time_ns,
                            "block_end_time_ns": (
                                block_start_time_ns + self._granularity_ns
                                if end_state != "THREAD_EXIT"
                                else last_event_time_ns
                            ),
                        }
                    )

                    # TODO: 1. Make a timeline of these blocks
                    #       2. Make a graph that shows this timeline
                    #          (like speedup stack but horizontal)

                    # old_values = per_lock_dict.setdefault(
                    #     caller,
                    #     {
                    #         "avg_wait": 0,
                    #         "count_wait": 0,
                    #         "max_wait": 0,
                    #         "total_wait": 0,
                    #         "avg_hold": 0,
                    #         "count_hold": 0,
                    #         "max_hold": 0,
                    #         "total_hold": 0,
                    #     },
                    # )

                    # per_lock_dict[caller].update(
                    #     {
                    #         avg_key: (
                    #             old_values[avg_key] * old_values[count_key]
                    #             + parsed_avg * parsed_count
                    #         )
                    #         / (old_values[count_key] + parsed_count),
                    #         count_key: old_values[count_key] + parsed_count,
                    #         max_key: max(old_values[max_key], parsed_max),
                    #         total_key: old_values[total_key] + parsed_total,
                    #     }
                    # )

            # __import__("pprint").pprint(per_thread_dict)
            self._per_run_per_thread_profile[self._run_counter] = per_thread_dict
            self._run_counter += 1
            return {}

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
