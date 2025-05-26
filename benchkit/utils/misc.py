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
    Context manager to enable measurement of the time in its scope.
    """

    def __init__(self):
        self.duration_seconds = 0
        self.start_time = 0
        self.end_time = 0

    def __enter__(self):
        self.start_time = datetime.datetime.now(tz=datetime.timezone.utc)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.datetime.now(tz=datetime.timezone.utc)
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()


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
