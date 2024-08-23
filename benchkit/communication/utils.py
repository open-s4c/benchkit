#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.utils.types import Command, Environment, PathType, SplitCommand


def format_arg(arg: str):
    if any(c.isspace() for c in arg):
        # the arg has whitespace, we add " " to avoid split of the shell
        return f'"{arg}"'
    return arg


def remote_shell_command(
    remote_command: Command,
    remote_current_dir: PathType | None = None,
) -> SplitCommand:
    if isinstance(remote_command, list):
        remote_formatted_command = " ".join(format_arg(a) for a in remote_command)
    else:
        remote_formatted_command = remote_command

    if remote_current_dir:
        cd_remote_command = f"cd {remote_current_dir} && {remote_formatted_command}"
    else:
        cd_remote_command = remote_formatted_command

    return cd_remote_command


def command_with_env(
    command: Command,
    environment: Environment,
    additional_environment: Environment,
) -> SplitCommand:
    full_environment = {}
    full_environment |= additional_environment
    if environment is not None:
        full_environment |= environment

    remote_env_lst = [f"{k}={full_environment[k]}" for k in full_environment]
    remote_env_str = " ".join(remote_env_lst)

    if isinstance(command, str):
        env_command = f"{remote_env_str} {command}"
    else:
        env_command = remote_env_lst + command

    return env_command
