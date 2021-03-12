#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Test asynchronous process error.
"""

import subprocess

from benchkit.platforms import get_current_platform
from benchkit.shell.shell import shell_out
from benchkit.shell.shellasync import AsyncProcess, shell_async

COMMAND = "taskset --cpu-list 1337 sleep 1"


def test_sync() -> None:
    """Test sync"""
    error_triggered = False
    try:
        shell_out(COMMAND)
    except subprocess.CalledProcessError as err:
        if 1 == err.returncode:
            error_triggered = True
    assert error_triggered


def test_async() -> None:
    """Test async"""
    error_triggered = False
    process = shell_async(
        command=COMMAND,
        stdout_path="/tmp/out.txt",
        stderr_path="/tmp/err.txt",
        platform=get_current_platform(),
    )
    try:
        process.wait()
    except AsyncProcess.AsyncProcessError as err:
        if 1 == err.returncode:
            error_triggered = True
    assert error_triggered


def main() -> None:
    """Main function of this test suite."""
    test_sync()
    test_async()


if __name__ == "__main__":
    main()
