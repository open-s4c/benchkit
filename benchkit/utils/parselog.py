# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities to parse logs.
"""

from typing import List

from benchkit.utils.types import PathType


def start_end_block(
    log_output: str,
    start: str,
    end: str,
) -> str:
    """
    Get block from a log output that starts and ends with the given string values.

    Args:
        log_output (PathType): text to parse.
        start (str): value at which to start recording the block.
        end (str): value at which to stop recording the block.

    Raises:
        ValueError: if block cannot be matched using start and end values.

    Returns:
        str: the block of text matching start and end.
    """
    log_size = len(log_output)

    i = log_size - 1
    i_end = -1
    i_start = -1
    while i > 0:
        if log_output[i:].startswith(end):
            i_end = i
            while i_end < log_size and "\n" != log_output[i_end]:
                i_end += 1
            break
        i -= 1

    if -1 == i_end:
        raise ValueError(f'No match for end block: "{end}"')

    while i > 0:
        if log_output[i:].startswith(start):
            i_start = i
            while i_start >= 0 and "\n" != log_output[i_start]:
                i_start -= 1
            i_start = max(i_start, 0)
            break
        i -= 1

    if -1 == i_start:
        raise ValueError(f'No match for start block: "{start}"')

    s = log_output[i_start:i_end]

    result = s.strip()
    return result


def loglines_from_module(
    log_output: str,
    start: str,
    end: str,
    module_name: str | None = None,
) -> List[str]:
    """
    Get the log lines from a specific module (in "dmesg" style) that matches start and end block.

    Args:
        log_output (str): text to parse.
        start (str): value at which to start recording the block.
        end (str): value at which to stop recording the block.
        module_name (str, optional): name of the module to get logs from. Defaults to None.

    Returns:
        List[str]: list of log lines from the given module.
    """
    log_block = start_end_block(
        log_output=log_output,
        start=start,
        end=end,
    )
    log_lines = [
        line for line in log_block.splitlines() if module_name is None or f"{module_name}:" in line
    ]
    return log_lines


def loglines_common_str(
    log_filename: PathType,
    common_str: str,
) -> List[str]:
    """
    Return lines of a logfile "log_filename" that contain a certain string "common_str".


    Args:
        log_filename (PathType): file to which parse the logs.
        common_str (str): common string to find in all lines returned.

    Returns:
        List[str]: all lines from given log file that contain the given common string.
    """
    with open(log_filename, "r") as log_file:
        log_lines = [line for line in log_file if common_str in line]
    return log_lines
