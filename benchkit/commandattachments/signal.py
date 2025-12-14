# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
This module defines an attachment that can send signals to the monitored process.

A typical use case involves chaining attachments. The first attachment signals the monitored
process to stop, allowing other attachments to complete their tasks.
The final attachment then sends a continue signal to start the benchmark.

Documentation of the types of signals can be found here:
    https://www.man7.org/linux/man-pages/man7/signal.7.html
"""

import os
import signal
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
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
    ) -> None:
        self._signal_type = signal_type

    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        os.kill(process.pid, self._signal_type)

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> None:
        pass
