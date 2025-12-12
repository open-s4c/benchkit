# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
This module defines an attachment that can send signals to the monitored process.

A typical use case involves chaining attachments. The first attachment signals the monitored
process to stop, allowing other attachments to complete their tasks.
The final attachment then sends a continue signal to start the benchmark.

Documentation of the types of signals can be found here:
    https://www.man7.org/linux/man-pages/man7/signal.7.html
"""

import signal

from benchkit.platforms import get_current_platform
from benchkit.platforms.generic import Platform
from benchkit.utils.types import PathType

class Signal:
    """
    This attachment sends a signal to the currently running benchmark

    Arguments:
        signal: the signal that should be sent to the process.
    """

    def __init__(
        self,
        signal_type: signal.Signals,
        platform: Platform = None,
    ) -> None:
        self._signal_type = signal_type
        self.platform = platform if platform is not None else get_current_platform()

    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        self.platform.comm.signal(process.pid, self._signal_type)
