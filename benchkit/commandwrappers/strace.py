# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `strace` utility that allows to trace all system calls used in the wrapped
command and output them into a file.
"""

import os
from typing import List, Optional

from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.types import PathType

class StraceWrap(CommandWrapper):
    """Command wrapper for the `strace` utility."""

    def __init__(
        self,
        summary: bool = True,
        summary_only: bool = False,
        trace_forks: bool = False,
        output_separately: bool = False,
    ):
        super().__init__()

        self._summary = summary
        self._summary_only = summary_only
        self._output_separately = output_separately
        self._trace_forks = trace_forks

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("strace"),
        ]

    def command_prefix(  # pylint: disable=arguments-differ
        self,
        record_data_dir: Optional[PathType],
        **kwargs,
    ) -> List[str]:
        cmd_prefix = super().command_prefix(**kwargs)

        if record_data_dir is None:
            raise ValueError(
                "Record data directory cannot be None, it is required to save strace output."
            )

        strace_output_pathname = os.path.join(record_data_dir, "strace.txt")

        options = []
        if self._summary:
            options.append("--summary")
        if self._summary_only:
            options.append("--summary-only")
        if self._output_separately:
            options.append("--output-separately")
        if self._trace_forks:
            options.append("--follow-forks")

        cmd_prefix = (
            ["strace"]
            + options
            + [
                "-o",
                f"{strace_output_pathname}",
            ]
            + cmd_prefix
        )

        return cmd_prefix
