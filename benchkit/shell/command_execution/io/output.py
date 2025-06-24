# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from abc import ABC
from typing import IO

from benchkit.shell.command_execution.io.stream import (
    EmptyIOStream,
    ReadableIOStream,
    PopenIOStream
)

class Output(ABC):
    """interface to communicate with command output on all platforms,
    functions are  due to compatibility"""

    def __init__(self, std_out: ReadableIOStream | None, std_err: ReadableIOStream | None):
        if std_out is None:
            std_out = EmptyIOStream()
        self.std_out: ReadableIOStream = std_out
        if std_err is None:
            std_err = EmptyIOStream()
        self.std_err: ReadableIOStream = std_err


def popen_get_output(out: IO[bytes] | None, err: IO[bytes] | None) -> Output:
    """Helper function to convert popen handles to an Output"""
    return Output(PopenIOStream(out) if out else None, PopenIOStream(err) if err else None)
