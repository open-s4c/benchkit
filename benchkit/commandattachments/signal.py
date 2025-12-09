# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shell import shell_out
from benchkit.utils.types import PathType
from enum import Enum

class SigSpec(Enum):
  SIGHUP = 1
  SIGINT = 2
  SIGQUIT = 3
  SIGILL = 4
  SIGTRAP = 5
  SIGABRT = 6
  SIGBUS = 7
  SIGFPE = 8
  SIGKILL = 9
  SIGUSR1 = 10
  SIGSEGV = 11
  SIGUSR2 = 12
  SIGPIPE = 13
  SIGALRM = 14
  SIGTERM = 15
  SIGSTKFLT = 16
  SIGCHLD = 17
  SIGCONT = 18
  SIGSTOP = 19
  SIGTSTP = 20
  SIGTTIN = 21
  SIGTTOU = 22
  SIGURG = 23
  SIGXCPU = 24
  SIGXFSZ = 25
  SIGVTALRM = 26
  SIGPROF = 27
  SIGWINCH = 28
  SIGIO = 29
  SIGPWR = 30
  SIGSYS = 31
  SIGRTMIN = 34
  SIGRTMIN_PLUS_1  = 35
  SIGRTMIN_PLUS_2 = 36
  SIGRTMIN_PLUS_3 = 37
  SIGRTMIN_PLUS_4 = 38
  SIGRTMIN_PLUS_5 = 39
  SIGRTMIN_PLUS_6 = 40
  SIGRTMIN_PLUS_7 = 41
  SIGRTMIN_PLUS_8 = 42
  SIGRTMIN_PLUS_9 = 43
  SIGRTMIN_PLUS_10 = 44
  SIGRTMIN_PLUS_11 = 45
  SIGRTMIN_PLUS_12 = 46
  SIGRTMIN_PLUS_13 = 47
  SIGRTMIN_PLUS_14 = 48
  SIGRTMIN_PLUS_15 = 49
  SIGRTMAX_MIN_14 = 50
  SIGRTMAX_MIN_13 = 51
  SIGRTMAX_MIN_12 = 52
  SIGRTMAX_MIN_11 = 53
  SIGRTMAX_MIN_10 = 54
  SIGRTMAX_MIN_9 = 55
  SIGRTMAX_MIN_8 = 56
  SIGRTMAX_MIN_7 = 57
  SIGRTMAX_MIN_6 = 58
  SIGRTMAX_MIN_5 = 59
  SIGRTMAX_MIN_4 = 60
  SIGRTMAX_MIN_3 = 61
  SIGRTMAX_MIN_2 = 62
  SIGRTMAX_MIN_1 = 63
  SIGRTMAX = 64

class Signal:
    """
    This attachment sends a signal to the currently running benchmark

    Arguments:
        signal: the signal that should be sent to the process.
    """

    def __init__(
        self,
        signal: SigSpec = None,
    ) -> None:
        self._signal = signal

    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        os.kill(process.pid, self._signal.value)

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> None:
        pass
