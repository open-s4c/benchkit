#!/usr/bin/env python3
# Copyright (C) 2024 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to test the use of pipe in local and remote execution.
"""

import sys
from benchkit.platforms import get_current_platform, get_remote_platform


def run_single_case(host, shell, expected_to_work) -> None:
    is_expected = {
        True: "###########\t\tExpected behavior\t\t###########",
        False: "###########\t\tUNEXPECTED BEHAVIOR!!!!\t\t###########",
    }

    if host == "local":
        my_host = get_current_platform()
    else:
        my_host = get_remote_platform(host=host)
        host = "remote"

    my_host.comm.shell("echo '' > QWERTY_zxcvb")
    try:
        output = my_host.comm.pipe_shell(
            "ls | grep QWERTY_zxcvb",
            shell=shell,
            print_command=False,
        )
        print(
            f"{is_expected[expected_to_work]} - Success with {host} execution and shell={shell}"
        )
        print(output)
    except:
        print(
            f"{is_expected[not expected_to_work]}"
            f" - Error occurs with {host} execution and shell={shell}"
        )


def run_default(host) -> None:
    if host == "local":
        my_host = get_current_platform()
    else:
        my_host = get_remote_platform(host=host)
        host = "remote"

    my_host.comm.shell("echo '' > QWERTY_zxcvb")
    try:
        output = my_host.comm.pipe_shell(
            "ls | grep QWERTY_zxcvb",
        )
        print(f"Success with {host} execution and default shell")
        print(output)
    except:
        print(f"!!!!!!Error occurs with {host} execution and default shell!!!!!!")


def test_local() -> None:
    run_single_case("local", True, True)
    run_single_case("local", False, False)


def test_remote(host_to_use) -> None:
    run_single_case(host_to_use, True, False)
    run_single_case(host_to_use, False, True)


def main() -> None:
    """Main function for this test suite."""

    if len(sys.argv) > 1:
        host_to_use = sys.argv[1]
    else:
        host_to_use = "node10"

    test_local()
    test_remote(host_to_use)
    print("")
    print("")
    print("")
    print("")
    print("")
    run_default("local")
    run_default(host_to_use)


if __name__ == "__main__":
    main()
