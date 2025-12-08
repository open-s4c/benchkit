# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.commandattachments.klockstat import Klockstat
from benchkit.utils.types import PathType

class SpeedupStackWrapper:
    def __init__(self,
                 libbpf_tools_dir: PathType) -> None:
        self._libbpf_tools_dir = libbpf_tools_dir

        self._klockstat = Klockstat(libbpf_tools_dir, pid=123)

    def command_wrappers(self):
        return []

    def command_attachments(self):
        return [self._klockstat.attachment]

    def post_run_hooks(self):
        return [self._klockstat.post_run_hook]
