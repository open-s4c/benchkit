#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT

"""Run tmux campaign dashboard on the remote host through SSH.

Usage:
    remotetmux.py [--campaign-dir <dirname>] <hosts>
    remotetmux.py (-h | --help)

Options:
    -h --help           Prints this help message.
    hosts               Comma-separated list of remote host names
                        (according to SSH config).
    --campaign-dir=DIR  Directory where to find the campaigns.
                        [default: campaigns]
"""

import os
import pathlib
import subprocess
from typing import Dict, List, Optional, Union

import docopt


def tiny_shell_out(
    cmd: Union[str, List[str]],
    cwd: Optional[str],
) -> str:
    """
    Execute a shell command. Tiny version of benchkit shell_out function.

    Args:
        cmd (Union[str, List[str]]):
            command to execute. Can be a string (with whitespaces) or a list of strings.
        cwd (Optional[str]):
            path to the directory where to execute the command.

    Returns:
        str: the output of the executed command.
    """
    cmd_lst = cmd.split(" ") if isinstance(cmd, str) else cmd
    result = subprocess.check_output(cmd_lst, text=True, cwd=cwd)
    return result


def cwd_git_root_dir() -> pathlib.Path:
    """
    Return the path to the git root directory according to the current directory of the script.

    Returns:
        pathlib.Path:
            the path to the git root directory according to the current directory of the script.
    """
    current = None
    while parent := tiny_shell_out(
        cmd="git rev-parse --show-superproject-working-tree",
        cwd=current,
    ).strip():
        current = parent

    output = tiny_shell_out(cmd="git rev-parse --show-toplevel", cwd=current).strip()
    result = pathlib.Path(output)
    return result


def remote_tmux(
    host: str,
    remote_campaigns_dir: str,
    remote_tmux_path: str,
) -> None:
    """
    Execute a command on the remote tmux.

    Args:
        host (str): remote host where to execute the command (through SSH).
        remote_campaigns_dir (str): path to directory where the benchkit campaigns are located.
        remote_tmux_path (str): path to the tmux script on the remote host.
    """
    remote_command = f"cd {remote_campaigns_dir} && {remote_tmux_path}"
    full_command = [
        "ssh",
        "-t",
        host,
        remote_command,
    ]
    result = tiny_shell_out(cmd=full_command, cwd=None)
    print(result)


def main(args: Dict[str, str]) -> None:
    """
    Main function of the script.

    Args:
        args (Dict[str, str]): docopt arguments.

    Raises:
        ValueError: if the tmux.py script is not found locally.
        ValueError: if the campaign directory is not found lcoally.
    """
    hosts_str = args["<hosts>"]
    campaign_dirname = args["--campaign-dir"]

    hosts = hosts_str.split(",")

    remote_tmux_path = pathlib.Path(__file__)
    script_dir = remote_tmux_path.parent
    tmux_path = script_dir / "tmux.py"
    if not tmux_path.is_file():
        raise ValueError(f'tmux.py not found locally: "{tmux_path}" path does not exist.')

    git_root_dir = cwd_git_root_dir()
    git_root_parent_dir, git_root_name = git_root_dir.parent, pathlib.Path(git_root_dir.name)

    tmux_rel_path = tmux_path.relative_to(git_root_parent_dir)
    username = os.getlogin()

    campaigns_rel_path = git_root_name / campaign_dirname
    campaigns_abs_path = git_root_parent_dir / campaigns_rel_path
    if not campaigns_abs_path.is_dir():
        raise ValueError(
            f'Campaigns directory not found locally: "{campaigns_abs_path}" does not exist.'
        )

    git_dir_remote = pathlib.Path(f"~/{username}/{git_root_name}")

    campaigns_path_remote = git_dir_remote / campaign_dirname
    tmux_path_remote = f"~/{username}/{tmux_rel_path}"

    for host in hosts:
        print(f"{host}:")
        remote_tmux(
            host=host,
            remote_campaigns_dir=str(campaigns_path_remote),
            remote_tmux_path=tmux_path_remote,
        )


if __name__ == "__main__":
    main(args=docopt.docopt(__doc__))
