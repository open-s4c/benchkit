# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from abc import ABC
from typing import IO

from benchkit.shell.CommunicationLayer.IO_stream import IOStream, SshIOStream


class Output(ABC):
    """interface to communicate with command output on all platforms,
    functions are  due to compatibility"""

    def __init__(self, std_out: IOStream | None, std_err: IOStream | None):
        if std_out is None:
            std_out = SshIOStream(None)
        self.std_out: IOStream = std_out
        if std_err is None:
            std_err = SshIOStream(None)
        self.std_err: IOStream = std_err


def sshOutput(out: IO[bytes] | None, err: IO[bytes] | None) -> Output:
    return Output(SshIOStream(out), SshIOStream(err))
