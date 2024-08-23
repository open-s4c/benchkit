# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities related to shell commands.
"""

import os
import pathlib
import re
import sys
import tempfile
from typing import Optional

from benchkit.utils.types import Command, Environment, PathType, SplitCommand


def get_args(command: Command) -> SplitCommand:
    """
    Convert a command into systematically split arguments (i.e., a list of string without
    whitespaces).

    Args:
        command (Command):
            command to convert into split command.

    Returns:
        SplitCommand: the split command.
    """
    if isinstance(command, str):
        arguments = command.split()
    else:
        arguments = command
    return arguments


def _print_cd(current_dir: PathType) -> None:
    print(f"[CD] {current_dir}")


def _print_env(environment: Environment) -> None:
    if environment is not None:
        for k in environment:
            print(f"[ENV:{k}] {environment[k]}")


def _shell_cmd(
    arguments: SplitCommand,
    environment: Environment,
    parallel: bool = False,
) -> str:
    def has_space(s: str) -> bool:
        return re.search(r"\s", s) is not None

    processed_args = [f'"{a}"' if has_space(a) else a for a in arguments]
    env_variables = [] if environment is None else [f'{k}="{environment[k]}"' for k in environment]
    result = " ".join(env_variables + processed_args) + (" &" if parallel else "")
    return result


def _print_run(
    arguments: SplitCommand,
    asynced: bool = False,
    remote_host: str | None = None,
) -> None:
    printed_command = " ".join(arguments)
    async_suffix = " async" if asynced else ""
    remote_suffix = f" REMOTELY ON {remote_host}" if remote_host is not None else ""
    print(f"[RUN{async_suffix}{remote_suffix}] {printed_command}")


def _print_shell_cmd(
    arguments: SplitCommand,
    current_dir: Optional[PathType],
    environment: Environment,
    remote_host: str | None,
) -> None:
    full_cmd_shell = _shell_cmd(arguments=arguments, environment=environment)
    print("[SHELL] To run in shell:")
    if remote_host is not None:
        print(f"  ssh {remote_host}")
    if current_dir is not None:
        real_current_dir = os.path.realpath(current_dir)
        print(f"  cd {real_current_dir}")
    print(f"  {full_cmd_shell}")


def _print_file_shell_cmd(
    arguments: SplitCommand,
    current_dir: Optional[PathType],
    environment: Environment,
    pathname: Optional[PathType] = None,
    parallel: bool = False,
    remote_host: str | None = None,
) -> None:
    if pathname is None:
        pathname = os.path.join(tempfile.gettempdir(), "benchkit.sh")

    header = []
    if not os.path.isfile(pathname):
        header = ["#!/bin/sh", "set -e", ""]

    if current_dir is None:
        current_dir = os.path.realpath(os.getcwd())

    remote_header = []
    remote_footer = []
    if remote_host is not None:
        remote_header = [f"# on remote {remote_host}:"]
        remote_footer = [f"# end commands on remote {remote_host}"]

    cd = [f"cd {current_dir}"]
    full_cmd_shell = _shell_cmd(
        arguments=arguments,
        environment=environment,
        parallel=parallel,
    )

    lines = [f"{line}\n" for line in header + remote_header + cd + [full_cmd_shell] + remote_footer]
    with open(pathname, "a") as shell_file:
        shell_file.writelines(lines)

    # TODO workaround before we implement more decent logging:
    campaign_log_path = pathlib.Path("/tmp/benchkit-campaign.sh")
    if campaign_log_path.is_file():
        with open(campaign_log_path, "a") as shell_file:
            shell_file.writelines(lines)



def print_header(
    arguments: SplitCommand,
    current_dir: Optional[PathType],
    environment: Environment,
    print_input: bool,
    print_env: bool,
    print_curdir: bool,
    print_shell_cmd: bool,
    print_file_shell_cmd: bool,
    asynced: bool,
    remote_host: str | None,
) -> None:
    """
    Print a header of command on benchkit logging.

    Args:
        arguments (SplitCommand):
            split command to print.
        current_dir (Optional[PathType]):
            current directory where the command is executed.
        environment (Environment):
            environment variables passed to the command.
        print_input (bool):
            whether to print the command. TODO rename print_command
        print_env (bool):
            whether to print the environment variables.
        print_curdir (bool):
            whether to print the current directory of the command.
        print_shell_cmd (bool):
            whether to print the shell command in a ready-to-be-copy-pasted format.
        print_file_shell_cmd (bool):
            whether to print the shell command in a log file (`/tmp/benchkit.sh`).
        asynced (bool):
            whether to command to print is asynchronous.
        remote_host (str | None):
            if the command is ran remotelly, the name of the remote host where it is executed.
    """
    if print_curdir and print_input and current_dir is not None:
        _print_cd(current_dir)

    if print_env and environment is not None:
        _print_env(environment)

    if print_input:
        _print_run(arguments=arguments, asynced=asynced, remote_host=remote_host)
    if print_shell_cmd:
        _print_shell_cmd(
            arguments=arguments,
            current_dir=current_dir,
            environment=environment,
            remote_host=remote_host,
        )

    if print_file_shell_cmd:
        _print_file_shell_cmd(
            arguments=arguments,
            current_dir=current_dir,
            environment=environment,
            parallel=asynced,
            remote_host=remote_host,
        )

    sys.stderr.flush()
    sys.stdout.flush()
