# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
This module defines an attachment that monitors the number of last layer cache misses
and number of references.

The documentation for the Python binding can be found here.
    https://man.docs.euro-linux.com/EL%209/bcc-tools/bcc-llcstat.8.en.html
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


class Llcstat(LibbpfTools):
    """
    Llcstat is an libbpf-tools util that monitors cache references and misses.
    NOTE: the llcstat utility requires added capabilities so that it
          can run with root privileges without sudo.

    Arguments:
        libbpf_tools_dir: the directory that points to the libbpf tools
        sample_period: Sample one in this many number of cache reference / miss events
    """

    def __init__(
        self,
        libbpf_tools_dir: PathType,
        sample_period: int = -1,
        platform: Platform = None,
    ) -> None:

        if libbpf_tools_dir == "":
            raise ValueError("The provided libbpf_tools_dir is empty")

        self._libbpf_tools_dir = libbpf_tools_dir
        self._sample_period = sample_period

        self.platform = platform if platform is not None else get_current_platform()

        self.out_file_name = "llcstat.out"
        self.err_file_name = "llcstat.err"

    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        self._pid = process.pid

        rdd = pathlib.Path(record_data_dir)

        lib_path = pathlib.Path(self._libbpf_tools_dir).as_posix()

        command = [lib_path + "/llcstat", "-t"]

        if self._sample_period > 0:
            command.extend(["-c", str(self._sample_period)])

        # Initialize AsyncProcess for llcstat
        self._process = AsyncProcess(
            platform=self.platform,
            arguments=command,
            stdout_path=rdd / self.out_file_name,
            stderr_path=rdd / self.err_file_name,
            current_dir=rdd,
        )

        # Wait until the clock stat has at least outputted something in the out file,
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
        self._process.send_signal(2, self._process.pid)
        self._process.wait()

        llcstat_out_file = os.path.join(record_data_dir, self.out_file_name)
        llcstat_err_file = os.path.join(record_data_dir, self.err_file_name)

        # if the error file is not empty print the content of the error file
        # and return an empty dictionary
        if os.stat(llcstat_err_file).st_size != 0:
            with open(llcstat_err_file) as err_file:
                for line in err_file.readlines():
                    print(line)
                return {}

        # This dictionary will hold all the aggregated values for each lock
        per_tid_dict = {}

        row_re = re.compile(r"^(\d+)\s+(\d+)\s+(.+\S)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+\.\d+)\%$")

        with open(llcstat_out_file) as out_file:
            for line in out_file.readlines():
                line = line.rstrip()

                m = row_re.search(line)
                if m:
                    line_pid = int(m.group(1))

                    if line_pid == self._pid:
                        tid = int(m.group(2))
                        name = m.group(3)
                        # cpu = int(m.group(4))
                        nr_references = int(m.group(5))
                        nr_misses = int(m.group(6))
                        hit_percentage = float(m.group(7))

                        old_values = per_tid_dict.setdefault(
                            tid,
                            {
                                "name": name,
                                # "cpu": 0,
                                "nr_references": 0,
                                "nr_misses": 0,
                                "hit_percentage": 0,
                            },
                        )

                        per_tid_dict[tid].update(
                            {
                                "nr_references": old_values["nr_references"] + nr_references,
                                "nr_misses": old_values["nr_misses"] + nr_misses,
                                "hit_percentage": (
                                    (
                                        (
                                            old_values["hit_percentage"]
                                            * old_values["nr_references"]
                                            + hit_percentage * nr_references
                                        )
                                        / (old_values["nr_references"] + nr_references)
                                    )
                                    if (old_values["nr_references"] + nr_references) > 0
                                    else 0
                                ),
                            }
                        )

        # Post run hooks must return a dictionary where each key at the top level corresponds
        # to some information to be kept. The current per-tid dictionary
        # does not adhere to this structure.

        total_nr_references = sum(d["nr_references"] for d in per_tid_dict.values())
        total_nr_misses = sum(d["nr_misses"] for d in per_tid_dict.values())

        total_nr_hits = total_nr_references - total_nr_misses
        avg_hit_percentage = (
            (total_nr_hits * 100 / total_nr_references) if total_nr_references != 0 else 0
        )
        return_dict = {
            "llcstat_total_nr_references": total_nr_references,
            "llcstat_total_nr_misses": total_nr_misses,
            "llcstat_avg_hit_percentage": avg_hit_percentage,
        }

        return return_dict
