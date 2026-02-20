# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `perf lock` Linux utility which allows to capture lock statistics
when executing the wrapped command.
"""

import pathlib
import re
import time
from threading import Thread
from typing import Any, Dict, List, Optional

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandwrappers.perf import PerfRecordWrap, _perf_command_prefix
from benchkit.helpers.linux import ps
from benchkit.platforms.generic import Platform
from benchkit.shell.shell import shell_out
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType, SplitCommand


class PerfLockWrap(PerfRecordWrap):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attachment_thread = None
        self._data_paths = {}

    def attach_every_thread(self, **kwargs):
        self.attachment_thread = Thread(target=self.attach_every_thread_worker, kwargs=kwargs)
        self.attachment_thread.start()

    def attach_every_thread_worker(
        self,
        process: AsyncProcess,
        platform: Platform,
        record_data_dir: pathlib.Path,
        poll_ms: int = 10,
    ):
        """Command attachment that will attach to every thread of the wrapped process.

        Args:
            process (AsyncProcess): the process to attach perf-stat to.
            platform (Platform): the platform where the process is running.
            record_data_dir (pathlib.Path): the path to the record data directory of the benchmark.
            poll_ms (int, optional): the period at which to poll the process to detect newly created
                                     threads. Defaults to 10.
        """
        perf_prefix = _perf_command_prefix(perf_bin=self._perf_bin, platform=platform)
        prefix = ["sudo"] + perf_prefix + ["lock", "record"] + self.perf_record_options + ["-t"]

        tids2perf_cmd = {}

        while not process.is_finished():
            current_tids = ps.get_threads_of_process(pid=process.pid, ignore_any_error_code=True)
            for tid in current_tids:
                if tid not in tids2perf_cmd:
                    perf_data_pathname = record_data_dir / f"perf-lock-record-tid-{tid}.data"
                    self._data_paths[tid] = perf_data_pathname
                    tids2perf_cmd[tid] = Thread(
                        target=self.attach_on_thread_worker,
                        kwargs={
                            "prefix": prefix,
                            "tid": tid,
                            "perf_data_pathname": perf_data_pathname,
                        },
                    )
                    tids2perf_cmd[tid].start()

            time.sleep(poll_ms / 1000)

        for current_process in tids2perf_cmd.values():
            try:
                current_process.join()
            except AsyncProcess.AsyncProcessError:
                pass

    def attach_on_thread_worker(
        self, prefix: list[str], tid: int, perf_data_pathname: pathlib.Path
    ):
        cmd = prefix + [f"{tid}", "--output", f"{perf_data_pathname}"]
        self.platform.comm.shell(command=cmd)

    def _perf_report_command(self, perf_data_pathname: PathType) -> SplitCommand:
        command = [
            self._perf_bin,
            "lock",
            "report",
            "--input",
            f"{perf_data_pathname}",
        ]

        return command

    def post_run_hook_report(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> Optional[Dict[str, Any]]:
        """Post run hook to generate extension of result dict holding the results of perf report.

        Args:
            experiment_results_lines (List[RecordResult]): the record results.
            record_data_dir (PathType): path to the record data directory.
            write_record_file_fun (WriteRecordFileFunction): callback to record a file into data
                                                             directory.
        """
        assert experiment_results_lines and record_data_dir
        assert self.attachment_thread is not None

        self.attachment_thread.join()

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

        row_re = re.compile(
            r"""
            ^\s+
            ([a-zA-Z]+)?\s+   # Optional name
            (\d+)\s+          # acquired
            (\d+)\s*          # contended
            (\S+\s\S+)\s*     # avg_wait
            (\S+\s\S+)\s*     # total_wait
            (\S+\s\S+)\s*     # max_wait
            (\S+\s\S+)\s*     # min_wait
            $
            """,
            re.VERBOSE,
        )

        aggregation_dict = {"perf_lock_total_wait_ns": 0.0}

        for tid, data_path in self._data_paths.items():
            self._chown(pathname=data_path)
            command = self._perf_report_command(perf_data_pathname=data_path)
            report_file = (record_data_dir / pathlib.Path(f"perf-tid-{tid}.report")).as_posix()

            # retrieve output into file first for posterity
            file_command = command + ["--output=" + report_file]
            shell_out(file_command, print_output=False)

            with open(report_file) as f:
                for line in f.readlines():
                    line = line.rstrip()
                    print(line)
                    m = row_re.search(line)
                    if m:
                        # name = m.group(1)
                        # acquired = int(m.group(2))
                        # contended = int(m.group(3))
                        # avg_wait = parse_time_to_ns(m.group(4))
                        total_wait = parse_time_to_ns(m.group(5))
                        # max_wait = parse_time_to_ns(m.group(6))
                        # min_wait = parse_time_to_ns(m.group(7))

                        aggregation_dict["perf_lock_total_wait_ns"] += total_wait

        self._data_paths = {}
        return aggregation_dict
