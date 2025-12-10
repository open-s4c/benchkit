# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pathlib
import re
import time
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType


class Offcputime:
    """
    Offcputime is an libbpf-tools util that monitors off CPU time.
    NOTE: the offcputime utility requires added capabilities so that it
          can run with root privileges without sudo.

    Arguments:
        libbpf_tools_dir: the directory that points to the libbpf tools
        pid: Trace these PIDs only, comma-separated list (TODO: support list of pids?)
        tid: Trace these TIDs only, comma-separated list (TODO: support list of tids?)
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
        tid: int = -1,
        kernel_threads_only: bool = False,
        user_threads_only: bool = False,
        min_block_time: int = -1,
        max_block_time: int = -1,
        perf_max_stack_depth: int = -1,
        stack_storage_size: int = -1,
        state: int = -1,
        platform: Platform = None,
    ) -> None:

        if libbpf_tools_dir == "":
            raise ValueError("The provided libbpf_tools_dir is empty")

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

        self.process = (None,)
        self.platform = platform if platform is not None else get_current_platform()

        self.out_file_name = "offcputime.out"
        self.err_file_name = "offcputime.err"

    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)

        lib_path = pathlib.Path(self._libbpf_tools_dir).as_posix()

        # command = ["sudo", lib_path + "/offcputime"]
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

        # Wait until the offcputime has at least outputted something in the out file,
        # or the error file, in order to know that it has attached the eBPF.
        while True:
            if (os.path.getsize(rdd / self.out_file_name) > 0) or (
                os.path.getsize(rdd / self.err_file_name) > 0
            ):
                break
            time.sleep(0.05)

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        pass
        self._process.send_signal(2, self._process.pid)
        self._process.wait()

        offcputime_out_file = os.path.join(record_data_dir, self.out_file_name)
        offcputime_err_file = os.path.join(record_data_dir, self.err_file_name)

        # if the error file is not empty print the content of the error file
        # and return an empty dictionary
        if os.stat(offcputime_err_file).st_size != 0:
            with open(offcputime_err_file) as err_file:
                for line in err_file.readlines():
                    print(line)
                return {}

        # This dictionary will hold all the aggregated values for each pid
        per_pid_dict = {}

        row_re = re.compile(r"^\((\S+\))\s+(\d+)\s+(\d+)$")

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

                    if old_values["name"] != name:
                        raise ValueError(
                            "The name of the old value was "
                            + old_values["name"]
                            + " but the new name is "
                            + name
                        )
                        # TODO: I'm unsure if this check is necessary.
                        # I have not encountered a benchmark yet that has
                        # different names for these PIDs.
                        # If the new name would be different than the old one,
                        # I am not sure if we could simply add the total of CPU time.

                    per_pid_dict[pid].update(
                        {
                            "name": name,
                            "total_off_time_micro_s": old_values["total_off_time_micro_s"]
                            + delta_micro_s,
                        }
                    )

        # __import__('pprint').pprint(per_pid_dict)
        """
            example output: It seems that the off-CPU time can be quite disproportionate
            depending on the threats. We'll need to properly look into how to use this data.
            Currently I will just do an average of all the off-CPU times, but this disregards
            the variation in the data.

            I will note that the average off-cpu time decreases with the number of threads.
            This might be due to the fact that the benchmark spawns a fixed number of threads
            for the database and that while using more threads these fixed number of threads
            are actually utilized.

            {190480: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 3023392},
             190483: {'name': 'rocksdb:rocksdb)', 'total_off_time_micro_s': 3028397},
             190484: {'name': 'rocksdb:rocksdb)', 'total_off_time_micro_s': 3028454},
             190485: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 429},
             190486: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 478},
             190487: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 315},
             190488: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 206},
             190489: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 207},
             190490: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 159},
             190491: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 93},
             190492: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 44},
             190493: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 13},
             190494: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 19},
             190495: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 39},
             190496: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 22},
             190497: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 11},
             190498: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 0},
             190499: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 0},
             190500: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 3007160},
             190501: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 220624},
             190502: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 203646},
             190503: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 217495},
             190504: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 226506},
             190505: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 204218},
             190506: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 212574},
             190507: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 205372},
             190508: {'name': 'db_benchdb_benc)', 'total_off_time_micro_s': 188601}}
        """

        number_of_pids = len(per_pid_dict.keys())
        return_dict = {
            "total_offcputime_micro_s": (
                (sum(d["total_off_time_micro_s"] for d in per_pid_dict.values()) / number_of_pids)
                if number_of_pids != 0
                else 0
            )
        }
        return return_dict
