# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import re
from collections import defaultdict
from pathlib import Path
from signal import SIGCONT, SIGSTOP
from threading import Thread
from typing import Any, Dict, List, Optional

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandattachments.klockstat import Klockstat
from benchkit.commandattachments.llcstat import Llcstat
from benchkit.commandattachments.offcputime import Offcputime
from benchkit.commandattachments.signal import Signal
from benchkit.commandwrappers import CommandWrapper
from benchkit.commandwrappers.perf import PerfRecordWrap
from benchkit.commandwrappers.strace import StraceWrap
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import get_current_platform
from benchkit.utils.types import PathType


class SpeedupStackWrapper(CommandWrapper):
    def __init__(self, libbpf_tools_dir: PathType) -> None:
        self._libbpf_tools_dir = libbpf_tools_dir

        self._klockstat = Klockstat(libbpf_tools_dir)
        self._offcputime = Offcputime(libbpf_tools_dir)
        self._llcstat = Llcstat(libbpf_tools_dir)
        self._strace = StraceWrap(pid=True, summary=False, summary_only=True)

        self._perf_record_lock = PerfRecordWrap(
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
            self._perf_record_lock_attachment,
            self._sigcont.attachment,
        ]

    # TODO: This does not seem to attach to every thread
    def _perf_record_lock_attachment(self, process, record_data_dir: Path):
        self._perf_record_lock_attachment_thread = Thread(
            target=self._perf_record_lock.attach_every_thread,
            kwargs={
                "platform": get_current_platform(),
                "process": process,
                "record_data_dir": record_data_dir,
            },
        )
        self._perf_record_lock_attachment_thread.start()
        # self._perf_record_lock.attach_every_thread(
        #     platform=get_current_platform(),
        #     process=process,
        #     record_data_dir=record_data_dir,
        # )

    def post_run_hooks(self):
        return [
            self._klockstat.post_run_hook,
            self._offcputime.post_run_hook,
            self._llcstat.post_run_hook,
            self._strace.post_run_hook,
            self._perf_record_lock_post_run_hook,
        ]

    def _perf_record_lock_post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> Optional[Dict[str, Any]]:
        assert self._perf_record_lock_attachment_thread is not None

        self._perf_record_lock_attachment_thread.join()

        self._perf_record_lock.post_run_hook_script(
            experiment_results_lines, record_data_dir, write_record_file_fun
        )

        row_re = re.compile(r"^\s*(\S+)\s+(\d+)\s+\[(\d+)\]\s+(\S+):\s+(\S+):\s+(.*)\s*$")
        script_file = record_data_dir / Path("perf.script")

        wait_start: Dict[int, float] = {}
        total_wait_time: float = 0.0
        total_wait_time_per_thread: Dict[int, float] = defaultdict(lambda: 0)

        with open(script_file) as f:
            for line in f.readlines():
                line = line.rstrip()
                m = row_re.search(line)
                if m:
                    comm = m.group(1)
                    tid = int(m.group(2))
                    cpu = int(m.group(3))
                    timestamp = int(round(float(m.group(4)) * 1e9))
                    event = m.group(5)
                    data = m.group(6)

                    if event == "syscalls:sys_enter_futex":
                        wait_start[tid] = timestamp

                    if event == "syscalls:sys_exit_futex":
                        if tid in wait_start:
                            wait_time_ns = timestamp - wait_start[tid]
                            total_wait_time += wait_time_ns
                            total_wait_time_per_thread[tid] += wait_time_ns
                            del wait_start[tid]

        return {"perf_record_lock_total_wait_ns": total_wait_time}

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
