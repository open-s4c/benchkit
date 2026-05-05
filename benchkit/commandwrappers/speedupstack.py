# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from signal import SIGCONT, SIGSTOP
from typing import List

from benchkit.commandattachments.klockstat import Klockstat
from benchkit.commandattachments.llcstat import Llcstat
from benchkit.commandattachments.offcputime import Offcputime
from benchkit.commandattachments.signal import Signal
from benchkit.commandattachments.threadprofiler import ThreadProfiler
from benchkit.commandwrappers import CommandWrapper
from benchkit.commandwrappers.jvmxlog import JVMXlogWrap
from benchkit.commandwrappers.strace import StraceWrap
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import get_current_platform
from benchkit.utils.types import PathType
from examples.rocksdb.cpiperfstatwrap import CPIPerfStatWrap


class SpeedupStackWrapper(CommandWrapper):
    def __init__(
        self,
        libbpf_tools_dir: PathType,
        thread_profiler_dir: PathType,
        output_duration: bool = False,
        jvm_plugin: bool = False,
    ) -> None:
        self._jvm_plugin = jvm_plugin

        self._libbpf_tools_dir = libbpf_tools_dir

        self._klockstat = Klockstat(libbpf_tools_dir)
        self._offcputime = Offcputime(libbpf_tools_dir, filter_comm=["rocksdb:rocksdb"])
        self._llcstat = Llcstat(libbpf_tools_dir)
        self._strace = StraceWrap(
            pid=True, summary=False, summary_only=True, filter_syscalls=["futex"]
        )
        self._cpi_perf = CPIPerfStatWrap(events=["cycles", "instructions"])
        self._threadprofiler = ThreadProfiler(
            thread_profiler_dir, self._cpi_perf, output_duration=output_duration
        )

        self._jvmxlogwrap = JVMXlogWrap()

        self._sigstop = Signal(signal_type=SIGSTOP)
        self._sigcont = Signal(signal_type=SIGCONT)

    def command_wrappers(self):
        return [self._jvmxlogwrap] if self._jvm_plugin else []

    def command_attachments(self):
        return [
            self._sigstop.attachment,
            # self._klockstat.attachment,
            # self._offcputime.attachment,
            # self._llcstat.attachment,
            # self._strace.attachment,
            lambda process, record_data_dir: self._cpi_perf.attachment(
                platform=get_current_platform(),
                process=process,
                record_data_dir=record_data_dir,
                poll_ms=10,
            ),
            self._threadprofiler.attachment,
            self._sigcont.attachment,
        ]

    def pre_run_hooks(self):
        return [self._threadprofiler.prerun_hook] + (
            [self._jvmxlogwrap.prerun_hook] if self._jvm_plugin else []
        )

    def post_run_hooks(self):
        return [
            # self._klockstat.post_run_hook,
            # self._offcputime.post_run_hook,
            # self._llcstat.post_run_hook,
            # self._strace.post_run_hook,
            # self.cpi_post_run_hook,
            self._cpi_perf.post_run_hook,
            self._threadprofiler.post_run_hook,
        ] + ([self._jvmxlogwrap.post_run_hook_update_results] if self._jvm_plugin else [])

    def dependencies(self) -> List[PackageDependency]:
        """Dependencies of the command wrapper.

        Returns:
            List[PackageDependency]: list of dependencies.
        """
        deps = []
        # deps.extend(self._klockstat.dependencies())
        # deps.extend(self._offcputime.dependencies())
        # deps.extend(self._llcstat.dependencies())

        return deps

    def get_threadprofiler(self):
        return self._threadprofiler
