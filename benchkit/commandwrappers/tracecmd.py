# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `trace-cmd` utility that allows to trace kernel events used in the wrapped
command and output them into a .dat file.
"""

import pathlib
from typing import List, Optional

from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.types import PathType


class TraceCmdWrap(CommandWrapper):
    """Command wrapper for the `trace-cmd` utility."""

    def __init__(
        self,
        tracecmd_prefix: str = "",
        events: List[str] = (),
    ):
        super().__init__()
        self._tracecmd = f"{tracecmd_prefix}trace-cmd"
        self._events = events

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("trace-cmd"),
        ]

    def command_prefix(  # pylint: disable=arguments-differ
        self,
        record_data_dir: Optional[PathType],
        **kwargs,
    ) -> List[str]:
        cmd_prefix = super().command_prefix(**kwargs)

        if record_data_dir is None:
            raise ValueError(
                "Record data directory cannot be None, it is required to save trace-cmd output."
            )

        tracecmd_output_pathname = pathlib.Path(record_data_dir) / "trace.dat"

        options = []

        for event in self._events:
            options.extend(["-e", event])

        cmd_prefix = (
            ["sudo", self._tracecmd, "record"]
            + options
            + [
                "-o",
                f"{tracecmd_output_pathname}",
            ]
            + cmd_prefix
        )

        return cmd_prefix
