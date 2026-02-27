# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import re
import time
from collections import defaultdict
from signal import SIGCONT, SIGSTOP
from threading import Thread
from typing import Any, Dict, List, Optional

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandattachments.klockstat import Klockstat
from benchkit.commandattachments.llcstat import Llcstat
from benchkit.commandattachments.offcputime import Offcputime
from benchkit.commandattachments.signal import Signal
from benchkit.commandwrappers import CommandWrapper
from benchkit.commandwrappers.perf import PerfRecordWrap, _perf_command_prefix
from benchkit.commandwrappers.strace import StraceWrap
from benchkit.dependencies.packages import PackageDependency
from benchkit.helpers.linux import ps
from benchkit.platforms import get_current_platform
from benchkit.platforms.generic import Platform
from benchkit.shell.shell import shell_out
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType


class SpeedupStackWrapper(CommandWrapper):
    def __init__(self, libbpf_tools_dir: PathType) -> None:
        self._libbpf_tools_dir = libbpf_tools_dir

        self._klockstat = Klockstat(libbpf_tools_dir)
        self._offcputime = Offcputime(libbpf_tools_dir)
        self._llcstat = Llcstat(libbpf_tools_dir)
        self._strace = StraceWrap(pid=True, summary=False, summary_only=True)

        self._perf_record_lock = PerfRecordLockWrap(
            perf_record_options=["-e", "syscalls:sys_enter_futex,syscalls:sys_exit_futex"],
            perf_report_options=["--ns"],
            report_file=True,
            report_interactive=False,
        )

        self._sigstop = Signal(signal_type=SIGSTOP)
        self._sigcont = Signal(signal_type=SIGCONT)

        self._perf_record_lock_attachment_thread = None

    def command_wrappers(self):
        return []

    def command_attachments(self):
        return [
            self._sigstop.attachment,
            self._klockstat.attachment,
            self._offcputime.attachment,
            self._llcstat.attachment,
            self._strace.attachment,
            lambda process, record_data_dir: self._perf_record_lock.attach_every_thread(
                platform=get_current_platform(),
                process=process,
                record_data_dir=record_data_dir,
            ),
            self._sigcont.attachment,
        ]

    def post_run_hooks(self):
        return [
            self._klockstat.post_run_hook,
            self._offcputime.post_run_hook,
            self._llcstat.post_run_hook,
            self._strace.post_run_hook,
            self._perf_record_lock.post_run_hook_script,
        ]

    def dependencies(self) -> List[PackageDependency]:
        """Dependencies of the command wrapper.

        Returns:
            List[PackageDependency]: list of dependencies.
        """
        deps = []
        deps.extend(self._klockstat.dependencies())
        deps.extend(self._offcputime.dependencies())
        deps.extend(self._llcstat.dependencies())

        return deps


class PerfRecordLockWrap(PerfRecordWrap):
    """
    This is a command wrapper for the `perf record` utility on multi-threaded benchmarks.
    """

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
        prefix = ["sudo"] + perf_prefix + ["record"] + self.perf_record_options + ["-t"]

        tids2perf_cmd = {}

        while not process.is_finished():
            current_tids = ps.get_threads_of_process(pid=process.pid, ignore_any_error_code=True)
            for tid in current_tids:
                if tid not in tids2perf_cmd:
                    perf_data_pathname = record_data_dir / f"perf-record-lock-val-tid-{tid}.txt"
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

    def post_run_hook_script(
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

        row_re = re.compile(r"^\s*(\S+)\s+(\d+)\s+\[(\d+)\]\s+(\S+):\s+(\S+):\s+(.*)\s*$")

        wait_start: Dict[int, int] = {}
        total_wait_time: int = 0
        total_wait_time_per_thread: Dict[int, int] = defaultdict(lambda: 0)

        for tid_of_file, data_path in self._data_paths.items():
            self._chown(pathname=data_path)
            command = self._perf_script_command(perf_data_pathname=data_path)
            script_file = (
                record_data_dir / pathlib.Path(f"perf-record-lock-tid-{tid_of_file}.script")
            ).as_posix()

            output = shell_out(command, print_output=False)

            write_record_file_fun(file_content=output.strip(), filename=script_file)

            for line in output.splitlines():
                line = line.rstrip()
                m = row_re.search(line)
                if m:
                    # comm = m.group(1)
                    tid = int(m.group(2))
                    # cpu = int(m.group(3))
                    timestamp = int(round(float(m.group(4)) * 1e9))
                    event = m.group(5)
                    # data = m.group(6)

                    if event == "syscalls:sys_enter_futex":
                        wait_start[tid] = timestamp

                    if event == "syscalls:sys_exit_futex":
                        if tid in wait_start:
                            wait_time_ns = timestamp - wait_start[tid]
                            total_wait_time += wait_time_ns
                            total_wait_time_per_thread[tid] += wait_time_ns
                            del wait_start[tid]

        self._data_paths = {}
        return {
            "perf_record_lock_total_wait_ns": total_wait_time,
            "perf_record_lock_thread_avg_wait_ns": (
                (total_wait_time / len(total_wait_time_per_thread))
                if len(total_wait_time_per_thread) != 0
                else 0
            ),
        }
