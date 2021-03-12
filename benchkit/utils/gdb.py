# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to interact with gdb.
"""

from benchkit.utils.types import Environment, PathType, SplitCommand


def generate_gdb_script_from_cmd(
    gdb_script_path: PathType,
    run_command: SplitCommand,
    environment: Environment,
):
    """
    Generate gdb script to run a given command.

    Args:
        gdb_script_path (PathType):
            the path where to write the generated gdb script.
        run_command (SplitCommand):
            command to run with the gdb script (for which it must be configured).
        environment (Environment):
            environment variables to pass to the command to run (in the gdb script as well).
    """
    run_command_lst = list(run_command)
    program = run_command_lst[0]
    args = " ".join(run_command_lst[1:])
    env_str = (
        " ".join([f'{k}="{environment[k]}"' for k in environment]) + " " if environment else ""
    )

    symbol_files = []
    if environment is not None and "LD_PRELOAD" in environment:
        symbol_files = [f"add-symbol-file {path}" for path in environment["LD_PRELOAD"].split(":")]

    gdb_script_lines = (
        [
            "# To run the program without gdb:",
            f"# {env_str} {program} {args}",
            "",
            "set confirm off",
            "set pagination off",
            "set startup-with-shell off",
            "",
        ]
        + ([f"set environment {k} {environment[k]}" for k in environment] if environment else [])
        + [
            "",
            f"file {program}",
        ]
        + symbol_files
        + ["", "break main", "", f"run {args}"]
    )

    with open(gdb_script_path, "w") as gdb_script:
        gdb_script.writelines([f"{line}\n" for line in gdb_script_lines])
