# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from typing import List

from benchkit.commandattachments.klockstat import Klockstat
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.types import PathType


class SpeedupStackWrapper(CommandWrapper):
    def __init__(self, libbpf_tools_dir: PathType) -> None:
        self._libbpf_tools_dir = libbpf_tools_dir

        self._klockstat = Klockstat(libbpf_tools_dir)

    def command_wrappers(self):
        return []

    def command_attachments(self):
        return [self._klockstat.attachment]

    def post_run_hooks(self):
        return [self._klockstat.post_run_hook]

    def dependencies(self) -> List[PackageDependency]:
        """Dependencies of the command wrapper.

        Returns:
            List[PackageDependency]: list of dependencies.
        """
        deps = []
        deps.extend(self._klockstat.dependencies())

        return deps
