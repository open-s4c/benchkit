# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `ltrace` utility that allows to trace all dynamic library calls used in the wrapped
command and output them into a file.
"""

import os
from typing import List, Optional

from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.types import PathType


class LtraceWrap(CommandWrapper):
    """Command wrapper for the `ltrace` utility."""

    def __init__(
        self,
        count_time_and_calls: bool = True,
        demangle_symbols: bool = False,
        debug_mask: str = "",
        call_filter: str = "",
        prototype_library_paths: str = "",
        trace_children: bool = False,
        show_instruction_pointer: bool = False,
        library_pattern: str = "",
        trace_pid: str = "",
        relative_timestamp: bool = False,
        display_syscalls: bool = False,
        show_time: bool = False,
        show_time_in_call: bool = False,
        symbol_entry_point_pattern: str = ""
    ):
        super().__init__()

        self._count_time_and_calls = count_time_and_calls
        self._demangle_symbols = demangle_symbols
        self._debug_mask = debug_mask
        self._call_filter = call_filter
        self._prototype_library_paths = prototype_library_paths
        self._trace_children = trace_children
        self._show_instruction_pointer = show_instruction_pointer
        self._library_pattern = library_pattern
        self._trace_pid = trace_pid
        self._relative_timestamp = relative_timestamp
        self._display_syscalls = display_syscalls
        self._show_time = show_time
        self._show_time_in_call = show_time_in_call
        self._symbol_entry_point_pattern = symbol_entry_point_pattern
        
    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("ltrace"),
        ]

    def command_prefix(  # pylint: disable=arguments-differ
        self,
        record_data_dir: Optional[PathType],
        **kwargs,
    ) -> List[str]:
        cmd_prefix = super().command_prefix(**kwargs)

        if record_data_dir is None:
            raise ValueError(
                "Record data directory cannot be None, it is required to save ltrace output."
            )

        strace_output_pathname = os.path.join(record_data_dir, "ltrace.txt")

        options = []
        if self._count_time_and_calls:
            options.append("-c")

        if self._demangle_symbols:
            options.append("-C")

        if self._debug_mask != "":
            options.append("-D " + self._debug_mask)

        if self._call_filter != "":
            options.append("-e " + self._call_filter)

        if self._prototype_library_paths != "":
            options.append("-F " + self._prototype_library_paths)

        if self._trace_children:
            options.append("-f")

        if self._show_instruction_pointer:
            options.append("-i")

        if self._library_pattern != "":
            options.append("-l " + self._library_pattern)

        if self._trace_pid != "":
            options.append("-p " + self._trace_pid)

        if self._relative_timestamp:
            options.append("-r")

        if self._display_syscalls:
            options.append("-S")

        if self._show_time:
            options.append("-t")

        if self._show_time_in_call:
            options.append("-T")
            
        if self._symbol_entry_point_pattern != "":
            options.append("-x " + self._symbol_entry_point_pattern)

        cmd_prefix = (
            ["ltrace"]
            + options
            + [
                "-o",
                f"{strace_output_pathname}",
            ]
            + cmd_prefix
        )

        return cmd_prefix
