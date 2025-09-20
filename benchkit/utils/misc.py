# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Miscellaneous functions.
"""

import datetime
import getpass
import os
import socket
import sys
from time import perf_counter_ns
from typing import Any, Dict

CSV_SEPARATOR = ";"


def hostname() -> str:
    """
    Return the hostname of the current host.
    TODO remove this function (in favor of platform.comm)

    Returns:
        str: the hostname of the current host.
    """
    return socket.gethostname()


def seconds2pretty(seconds: float) -> str:
    """
    Convert seconds into a pretty representation of time.

    Args:
        seconds (int): seconds to convert.

    Returns:
        str: a pretty representation of the given duration.
    """
    result = str(datetime.timedelta(seconds=seconds))
    return result


def dict_union(
    d1: Dict[Any, Any],
    d2: Dict[Any, Any],
) -> Dict[Any, Any]:
    """
    Return the union of the two given dict, i.e., d1 | d2.

    Args:
        d1 (Dict[Any, Any]): left dict.
        d2 (Dict[Any, Any]): right dict.

    Returns:
        Dict[Any, Any]: the union of the left and the right dict.
    """
    if sys.version_info < (3, 9):
        return {**d1, **d2}
    return d1 | d2


class TimeMeasure:
    """
    Monotonic, high-resolution timing context manager.
    Usage:
        with TimeMeasure() as tm:
            do_work()
        print(tm.seconds, tm.milliseconds, tm.microseconds)
        print(tm.as_unit('ms'))
    """

    __slots__ = ("_t0", "_t1", "duration_ns", "start_time")

    def __init__(self):
        self._t0 = 0
        self._t1 = 0
        self.duration_ns = 0  # int, nanoseconds
        self.start_time = datetime.datetime(1970, 1, 1)

    def __enter__(self):
        self.start_time = datetime.datetime.now(tz=datetime.timezone.utc)
        self._t0 = perf_counter_ns()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._t1 = perf_counter_ns()
        self.duration_ns = self._t1 - self._t0

    @property
    def seconds(self) -> float:
        return self.duration_ns / 1_000_000_000

    @property
    def milliseconds(self) -> float:
        return self.duration_ns / 1_000_000

    @property
    def microseconds(self) -> float:
        return self.duration_ns / 1_000

    @property
    def duration_seconds(self):
        return self.seconds

    # Generic accessor
    def as_unit(self, unit: str = "s") -> float:
        unit = unit.lower()
        if unit in ("s", "sec", "secs", "second", "seconds"):
            return self.seconds
        if unit in ("ms", "millisecond", "milliseconds"):
            return self.milliseconds
        if unit in ("us", "µs", "microsecond", "microseconds"):
            return self.microseconds
        if unit in ("ns", "nanosecond", "nanoseconds"):
            return float(self.duration_ns)
        raise ValueError(f"Unknown unit: {unit}")

    def __repr__(self):
        return f"<TimeMeasure {self.milliseconds:.3f} ms>"


def get_user_name() -> str:
    return getpass.getuser()


def get_benchkit_temp_folder_str() -> str:
    path: str = f"/tmp/benchkit-{get_user_name()}"
    os.makedirs(os.path.dirname(f"{path}/"), exist_ok=True)
    return path


if __name__ == "__main__":
    # straightforward test for TimeMeasure context manager
    import time

    with TimeMeasure() as my_time:
        time.sleep(0.5)
    print(my_time.duration_seconds)

    with TimeMeasure() as tm:
        time.sleep(0.5)
    print(tm.seconds, tm.milliseconds, tm.microseconds)
    print(tm.as_unit("ms"))
