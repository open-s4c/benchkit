# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
TODO
"""

import math
import os
import pathlib
import re
from collections import defaultdict
from typing import List, Tuple

from numpy import mean

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
        platform: Platform = None,
    ) -> None:

        self.platform = platform if platform is not None else get_current_platform()

        if not self.platform.comm.path_exists(thread_profiler_dir):
            raise ValueError("The provided thread_profiler_dir does not exist")

        self._thread_profiler_dir = thread_profiler_dir
        self._pid = pid
        self._tid = tid
        self._granularity_ns = int(1e8)
        self._per_run_per_thread_profile = {}
        self._run_counter = 1

        self.out_file_name = "threadprofiler.out"
        self.err_file_name = "threadprofiler.err"

        self._nb_threads = 0
        self._enabled = True

    def attachment(
        self,
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:

        if not self._enabled:
            return

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

    def prerun_hook(
        self,
        build_variables: RecordResult,
        run_variables: RecordResult,
        other_variables: RecordResult,
        record_data_dir: PathType,
    ) -> None:
        if "nb_threads" not in run_variables:
            print("ERROR: threadprofiler expects the 'nb_threads' variable to be present")
            return

        self._nb_threads = run_variables["nb_threads"]

        if "threadprofiler_enabled" in run_variables:
            self._enabled = run_variables["threadprofiler_enabled"]
        if "threadprofiler_granularity" in run_variables:
            self._granularity_ns = run_variables["threadprofiler_granularity"]

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:

        if not self._enabled:
            return {}

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
        per_thread_dict: dict[int, dict] = defaultdict(
            lambda: {
                "blocks": [],
                "merged": {
                    "block_index": -math.inf,
                    "block_start_time_ns": math.inf,
                    "block_end_time_ns": -math.inf,
                    "offcpu_time_ns": 0,
                    "mutex_time_ns": 0,
                    "futex_time_ns": 0,
                    "disk_io_time_ns": 0,
                    "cutoff_time_ns": None,
                },
            }
        )
        row_re = re.compile(
            r"^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*(\d+)?\s*$"
        )

        with open(threadprofiler_out_file) as out_file:
            for line in out_file.readlines():
                line = line.rstrip()

                m = row_re.search(line)
                if m:
                    tid = int(m.group(1))
                    block_index = int(m.group(2))
                    block_start_time_ns = int(m.group(3))
                    block_end_time_ns = int(m.group(4))
                    offcpu_time_ns = int(m.group(5))
                    mutex_time_ns = int(m.group(6))
                    futex_time_ns = int(m.group(7))
                    disk_io_time_ns = int(m.group(8))
                    cutoff_time_ns = int(m.group(9)) if m.group(9) else None

                    merged = per_thread_dict[tid]["merged"]
                    if merged["block_index"] < block_index:
                        merged["block_index"] = block_index

                        if merged["block_start_time_ns"] > block_start_time_ns:
                            merged["block_start_time_ns"] = block_start_time_ns
                        if cutoff_time_ns:
                            merged["block_end_time_ns"] = cutoff_time_ns
                            merged["cutoff_time_ns"] = cutoff_time_ns
                        elif merged["block_end_time_ns"] < block_end_time_ns:
                            merged["block_end_time_ns"] = block_end_time_ns

                        merged["offcpu_time_ns"] += offcpu_time_ns
                        merged["mutex_time_ns"] += mutex_time_ns
                        merged["futex_time_ns"] += futex_time_ns
                        merged["disk_io_time_ns"] += disk_io_time_ns

                        per_thread_dict[tid]["blocks"].append(
                            {
                                "block_index": block_index,
                                "block_start_time_ns": block_start_time_ns,
                                "block_end_time_ns": block_end_time_ns,
                                "offcpu_time_ns": offcpu_time_ns,
                                "mutex_time_ns": mutex_time_ns,
                                "futex_time_ns": futex_time_ns,
                                "disk_io_time_ns": disk_io_time_ns,
                                "cutoff_time_ns": cutoff_time_ns,
                            }
                        )

            self._per_run_per_thread_profile[self._run_counter] = per_thread_dict
            self._run_counter += 1

        # Detect the benchmarking threads using heuristic
        # For now the heuristic will contain two part:
        # 1. There are exactly nb_threads benchmarking threads
        # 2. The benchmarking threads perform the most 'useful' of all the threads
        #    with the pid of the benchmark
        def add_thread_useful_work(x: Tuple[int, dict]) -> None:
            merged_block = x[1]["merged"]
            block_duration = merged_block["block_end_time_ns"] - merged_block["block_start_time_ns"]
            merged_block["useful_work_time_ns"] = (
                block_duration
                - merged_block["offcpu_time_ns"]
                - merged_block["mutex_time_ns"]
                - merged_block["futex_time_ns"]
                - merged_block["disk_io_time_ns"]
            )

        def get_thread_useful_work(x: Tuple[int, dict]) -> int:
            return x[1]["merged"]["useful_work_time_ns"]

        def benchmarking_thread_exit(x: Tuple[int, dict]) -> int:
            merged_block = x[1]["merged"]
            return merged_block["block_end_time_ns"]

        per_thread_list = list(per_thread_dict.items())

        if len(per_thread_list) == 0:
            return {}

        for thread in per_thread_list:
            add_thread_useful_work(thread)

        sorted_by_useful_work = sorted(per_thread_list, key=get_thread_useful_work, reverse=True)

        # __import__("pprint").pprint(sorted_by_schedule_in)

        benchmarking_threads = sorted_by_useful_work[: self._nb_threads]
        # __import__("pprint").pprint(benchmarking_threads)
        benchmarking_tids = list(map(lambda x: x[0], benchmarking_threads))

        last_benchmarking_thread_to_exit_time_ns = max(
            list(map(benchmarking_thread_exit, benchmarking_threads))
        )

        max_useful_work_time_ns = benchmarking_threads[0][1]["merged"]["useful_work_time_ns"]

        # print("max_useful_work_time_ns", max_useful_work_time_ns)

        # To find the main thread we use the property that the spawned threads
        # have higher TIDs than their parent
        main_thread_tuple = sorted(per_thread_list, key=lambda x: x[0])[0]
        main_thread_tid = main_thread_tuple[0]
        main_thread_dict = main_thread_tuple[1]

        # Find initialization component
        main_thread_merged = main_thread_dict["merged"]
        main_thread_start_ts = main_thread_merged["block_start_time_ns"]
        total_run_duration = main_thread_merged["block_end_time_ns"] - main_thread_start_ts

        mean_initialization_time = int(
            mean(
                list(
                    map(
                        lambda x: x[1]["merged"]["block_start_time_ns"] - main_thread_start_ts,
                        benchmarking_threads,
                    )
                )
            )
        )

        # Combine the benchmarking thread merged profile blocks to create the slowdown components

        mean_offcpu_time_ns = int(
            mean(list(map(lambda x: x[1]["merged"]["offcpu_time_ns"], benchmarking_threads)))
        )
        mean_mutex_time_ns = int(
            mean(list(map(lambda x: x[1]["merged"]["mutex_time_ns"], benchmarking_threads)))
        )
        mean_futex_time_ns = int(
            mean(list(map(lambda x: x[1]["merged"]["futex_time_ns"], benchmarking_threads)))
        )
        mean_disk_io_time_ns = int(
            mean(list(map(lambda x: x[1]["merged"]["disk_io_time_ns"], benchmarking_threads)))
        )

        mean_literature_load_imbalance_time_ns = int(
            mean(
                list(
                    map(
                        lambda x: last_benchmarking_thread_to_exit_time_ns
                        - x[1]["merged"]["block_end_time_ns"],
                        benchmarking_threads,
                    )
                )
            )
        )

        mean_propoped_load_imbalance_time_ns = int(
            mean(
                list(
                    map(
                        lambda x: max_useful_work_time_ns - x[1]["merged"]["useful_work_time_ns"],
                        benchmarking_threads,
                    )
                )
            )
        )

        return {
            "threadprofiler_initialization_ns": mean_initialization_time,
            "threadprofiler_offcpu_ns": mean_offcpu_time_ns,
            "threadprofiler_mutex_ns": mean_mutex_time_ns,
            "threadprofiler_futex_ns": mean_futex_time_ns,
            "threadprofiler_disk_io_ns": mean_disk_io_time_ns,
            "threadprofiler_literature_load_imbalance_ns": mean_literature_load_imbalance_time_ns,
            "threadprofiler_proposed_load_imbalance_ns": mean_propoped_load_imbalance_time_ns,
        }
