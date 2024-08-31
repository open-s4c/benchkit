# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interactions with a shell.
"""

import subprocess
import sys
from typing import Iterable, Optional

from benchkit.shell.utils import get_args, print_header
from benchkit.utils.types import Command, Environment, PathType


def pipe_shell_out(
    command: Command,
    current_dir: Optional[PathType] = None,
    shell: bool = True,
    print_command: bool = True,
    ignore_ret_codes: Iterable[int] = (),
) -> str:
    """
    Run a command that is a composition of shell through pipes.
    For example: `commandA | commandB`

    Args:
        command (Command):
            the piped command.
        current_dir (Optional[PathType], optional):
            the directory where the piped command is expected to run.
            Defaults to None.

    Returns:
        str: the output of the piped command.
    """
    arguments = get_args(command)
    if print_command:
        print_header(
            arguments=arguments,
            current_dir=current_dir,
            environment=None,
            print_input=True,
            print_env=True,
            print_curdir=True,
            print_shell_cmd=True,
            print_file_shell_cmd=True,
            asynced=False,
            remote_host=None,
        )

    try:
        output = subprocess.check_output(
            command,
            cwd=current_dir,
            shell=shell,
            text=True
        )

    except subprocess.CalledProcessError as err:
        retcode = err.returncode
        if retcode not in ignore_ret_codes:
            raise err
        output = err.output

    return output


def shell_out(
    command: Command,
    std_input: Optional[str] = None,
    current_dir: Optional[PathType] = None,
    environment: Environment = None,
    shell: bool = False,
    print_input: bool = True,
    print_output: bool = True,
    print_env: bool = True,
    print_curdir: bool = True,
    print_shell_cmd: bool = False,
    print_file_shell_cmd: bool = True,
    timeout: Optional[int] = None,
    output_is_log: bool = False,
    ignore_ret_codes: Iterable[int] = (),
    ignore_any_error_code: bool = False,
) -> str:
    """
    Run a shell command on the host system.

    Args:
        command (Command):
            the command to run.
        std_input (Optional[str], optional):
            input to feed to the command.
            Defaults to None.
        current_dir (Optional[PathType], optional):
            directory where to run the command. If None, the current directory is used.
            Defaults to None.
        environment (Environment, optional):
            environment variables to pass to the command.
            Defaults to None.
        shell (bool, optional):
            whether to run the command in a shell environment (like "bash") or as a real command
            given to "exec".
            Defaults to False.
        print_input (bool, optional):
            whether to print the command. TODO should be renamed "print_command"
            Defaults to True.
        print_output (bool, optional):
            whether to print the output.
            Defaults to True.
        print_env (bool, optional):
            whether to print the environment variables when they are defined.
            Defaults to True.
        print_curdir (bool, optional):
            whether to print the current directory if provided.
            Defaults to True.
        print_shell_cmd (bool, optional):
            whether to print the complete shell command, ready to be copy-pasted in a terminal.
            Defaults to False.
        print_file_shell_cmd (bool, optional):
            whether to print the shell command in a log file (`/tmp/benchkit.sh`).
            Defaults to True.
        timeout (Optional[int], optional):
            if not None, the command will be stopped after `timeout` seconds if it did not stop
            earlier.
            Defaults to None.
        output_is_log (bool, optional):
            whether the output of this command is logging and should be outputted as such, line by
            line (e.g. cmake or make command).
            Defaults to False.
        ignore_ret_codes (Iterable[int], optional):
            collection of error return codes to ignore if they are triggered.
            This allows to avoid an exception to be raised for commands that do not end with 0 even
            if they are successful.
            Defaults to ().
        ignore_any_error_code (bool, optional):
            whether to error any error code returned by the command.

    Raises:
        subprocess.CalledProcessError:
            if the command exited with a non-zero exit code that is not ignored in
            `ignore_ret_codes`.

    Returns:
        str: the output of the shell command that completed successfully.
    """
    arguments = get_args(command)
    print_header(
        arguments=arguments,
        current_dir=current_dir,
        environment=environment,
        print_input=print_input,
        print_env=print_env,
        print_curdir=print_curdir,
        print_shell_cmd=print_shell_cmd,
        print_file_shell_cmd=print_file_shell_cmd,
        asynced=False,
        remote_host=None,
    )

    if output_is_log:

        def flush_outlines():
            raw_outline = process.stdout.readline()
            while raw_outline:
                outline = raw_outline.decode()
                print(outline, end="")
                outlines.append(outline)
                raw_outline = process.stdout.readline()

        outlines = []
        with subprocess.Popen(
            arguments,
            shell=shell,
            cwd=current_dir,
            env=environment,
            stdout=subprocess.PIPE,
        ) if std_input is None else subprocess.Popen(
            arguments,
            shell=shell,
            cwd=current_dir,
            env=environment,
            stdout=subprocess.PIPE,
            stdin=std_input,
            text=True,
        ) as process:
            retcode = process.poll()
            while retcode is None:
                flush_outlines()
                retcode = process.poll()
            flush_outlines()
        output = "".join(outlines)

        sys.stdout.flush()
        sys.stderr.flush()

        if retcode:
            raise subprocess.CalledProcessError(
                retcode,
                process.args,
            )
    else:
        try:
            if std_input is not None:
                output = subprocess.check_output(
                    arguments,
                    shell=shell,
                    cwd=current_dir,
                    env=environment,
                    timeout=timeout,
                    input=std_input,
                    text=True,
                )

            else:
                output = subprocess.check_output(
                    arguments,
                    shell=shell,
                    cwd=current_dir,
                    env=environment,
                    timeout=timeout,
                    text=True,
                )
        except subprocess.CalledProcessError as err:
            retcode = err.returncode
            if ignore_any_error_code:
                pass
            elif retcode in ignore_ret_codes:
                pass
            else:
                raise err
            output = err.output

    if print_output and not output_is_log:
        if "" != output.strip():
            print("[OUT]")
            print(output.strip())

    assert isinstance(output, str)
    return output


def shell_interactive(
    command: Command,
    current_dir: Optional[PathType] = None,
    environment: Environment = None,
    shell: bool = False,
    print_input: bool = True,
    print_env: bool = True,
    print_curdir: bool = True,
    print_shell_cmd: bool = False,
    print_file_shell_cmd: bool = True,
    ignore_ret_codes: Iterable[int] = (),
) -> None:
    """
    Run a shell command that is interactive (with prompts, etc.).

    Args:
        command (Command):
            the command to run.
        current_dir (Optional[PathType], optional):
            directory where to run the command. If None, the current directory is used.
            Defaults to None.
        environment (Environment, optional):
            environment variables to pass to the command.
            Defaults to None.
        shell (bool, optional):
            whether to run the command in a shell environment (like "bash") or as a real command
            given to "exec".
            Defaults to False.
        print_input (bool, optional):
            whether to print the command. TODO should be renamed "print_command"
            Defaults to True.
        print_env (bool, optional):
            whether to print the environment variables when they are defined.
            Defaults to True.
        print_curdir (bool, optional):
            whether to print the current directory if provided.
            Defaults to True.
        print_shell_cmd (bool, optional):
            whether to print the complete shell command, ready to be copy-pasted in a terminal.
            Defaults to False.
        print_file_shell_cmd (bool, optional):
            whether to print the shell command in a log file (`/tmp/benchkit.sh`).
            Defaults to True.
        ignore_ret_codes (Iterable[int], optional):
            collection of error return codes to ignore if they are triggered.
            This allows to avoid an exception to be raised for commands that do not end with 0 even
            if they are successful.
            Defaults to ().

    Raises:
        subprocess.CalledProcessError:
            if the command exited with a non-zero exit code that is not ignored in
            `ignore_ret_codes`.
    """
    arguments = get_args(command)
    print_header(
        arguments=arguments,
        current_dir=current_dir,
        environment=environment,
        print_input=print_input,
        print_env=print_env,
        print_curdir=print_curdir,
        print_shell_cmd=print_shell_cmd,
        print_file_shell_cmd=print_file_shell_cmd,
        asynced=False,
        remote_host=None,
    )

    process = subprocess.Popen(
        arguments,
        shell=shell,
        cwd=current_dir,
        env=environment,
    )
    process.wait()
    retcode = process.poll()

    if 0 != retcode and retcode not in ignore_ret_codes:
        raise subprocess.CalledProcessError(
            retcode,
            process.args,
        )
