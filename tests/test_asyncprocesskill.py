#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to test the killing of asynchronous processes.
"""

from benchkit.platforms import get_current_platform
from benchkit.shell.shellasync import AsyncProcess, shell_async


def test_kill_alreadydone() -> None:
    """Test to kill an asynchronous process that has already finished executing."""
    error_triggered = False
    process = shell_async(
        command="echo test",
        stdout_path="/tmp/out.txt",
        stderr_path="/tmp/err.txt",
        platform=get_current_platform(),
    )
    try:
        process.stop()
    except AsyncProcess.AsyncProcessError as ape:
        return_code = ape.returncode
        assert 0 == return_code
        error_triggered = True
    assert error_triggered


def test_kill_sleep() -> None:
    """Test to kill a asynchronous process that is sleeping."""
    process = shell_async(
        command="sleep 600",
        stdout_path="/tmp/out.txt",
        stderr_path="/tmp/err.txt",
        platform=get_current_platform(),
    )
    process.stop()


def main() -> None:
    """Main function for this test suite."""
    test_kill_alreadydone()
    test_kill_sleep()


if __name__ == "__main__":
    main()
