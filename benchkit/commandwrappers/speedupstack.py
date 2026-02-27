# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from signal import SIGCONT, SIGSTOP
from typing import List

from benchkit.commandattachments.klockstat import Klockstat
from benchkit.commandattachments.llcstat import Llcstat
from benchkit.commandattachments.offcputime import Offcputime
from benchkit.commandattachments.signal import Signal
from benchkit.commandwrappers import CommandWrapper
from benchkit.commandwrappers.strace import StraceWrap
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.types import PathType


class SpeedupStackWrapper(CommandWrapper):
    def __init__(self, libbpf_tools_dir: PathType) -> None:
        self._libbpf_tools_dir = libbpf_tools_dir

        self._klockstat = Klockstat(libbpf_tools_dir)
        self._offcputime = Offcputime(libbpf_tools_dir)
        self._llcstat = Llcstat(libbpf_tools_dir)
        self._strace = StraceWrap(
            pid=True, summary=False, summary_only=True, filter_syscalls=["futex"]
        )

        self._sigstop = Signal(signal_type=SIGSTOP)
        self._sigcont = Signal(signal_type=SIGCONT)

    def command_wrappers(self):
        return []

    def command_attachments(self):
        return [
            self._sigstop.attachment,
            self._klockstat.attachment,
            self._offcputime.attachment,
            self._llcstat.attachment,
            self._strace.attachment,
            self._sigcont.attachment,
        ]

    def post_run_hooks(self):
        return [
            self._klockstat.post_run_hook,
            self._offcputime.post_run_hook,
            self._llcstat.post_run_hook,
            self._strace.post_run_hook,
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
