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

from multiprocessing import Process,Queue

def pipe_shell_out(
    command: Command,
    current_dir: Optional[PathType] = None,
    print_output: bool = True,
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
    return shell_out(
        command = command,
        current_dir = current_dir,
        shell = True,
        print_shell_cmd=True,
        split_arguments=False,
        print_output=print_output
    )


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
    split_arguments: bool = True,
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
        split_arguments (bool, optional):
            whether the command is split in parts.
            This allows for the usage of commands using things like the pipe symbol, use with shell=True for this functionality.
            Defaults to True.

    Raises:
        subprocess.CalledProcessError:
            if the command exited with a non-zero exit code that is not ignored in
            `ignore_ret_codes`.

    Returns:
        str: the output of the shell command that completed successfully.
    """

    #this will run the true command confirming the exit code instead of assuming it
    completedProcess = subprocess.run(["true"], timeout=None)
    sucsess_value = completedProcess.returncode
    def sucsess(value):
        return value == sucsess_value


    print_arguments = get_args(command)
    print_header(
        arguments=print_arguments,
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

    #splitting our command as needed
    arguments = get_args(command) if (split_arguments)  else command


    def flush_outlines(process):
        """
        prints and returns the current content of stdout for a given process
        Args:
            process (Popen):
                process to log
        Returns:
            str: content of stdout.
        """
        outlines = []
        outline = process.stdout.readline()
        while outline:
            print(outline, end="")
            outlines.append(outline)
            outline = process.stdout.readline()
        return outlines

    def flush_thread(process,output_queue):
        """
        while process is running will log and store all stdout in real time
        Args:
            process (Popen):
                process to log
            output_queue (Queue):
                Queue to write the returned value to
        Returns:
            None
        """
        outlines = []
        retcode = process.poll()
        while retcode is None:
            outlines += flush_outlines(process)
            retcode = process.poll()
        outlines += flush_outlines(process)
        sys.stdout.flush()
        sys.stderr.flush()
        output_queue.put( "".join(outlines))
     
    with subprocess.Popen(
        arguments,
        shell=shell,
        cwd=current_dir,
        env=environment,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True,
    ) as shell_process:
        if output_is_log:
            try:
                """
                logging the process takes two threads since we need to wait for the timeout while logging stdout in real time
                to accomplish this we use multiprocessing in combination with error catching to interupt the logging if needed
                """
                output_queue = Queue()
                logger_process = Process(target=flush_thread, args=(shell_process,output_queue,))
                logger_process.start()
                outs, errs = shell_process.communicate(input=std_input, timeout=timeout)
                retcode = shell_process.poll()
                output = output_queue.get()

            except subprocess.TimeoutExpired as err:
                shell_process.kill()
                logger_process.terminate()
                raise err

        else:
            try:
                outs, errs = shell_process.communicate(input=std_input, timeout=timeout)
                retcode = shell_process.poll()
                output = outs
            except subprocess.TimeoutExpired as err:
                shell_process.kill()
                raise err

        #not a sucsessfull execution and not an alowed exit code
        #raise the appropriate error
        if not sucsess(retcode) and retcode not in ignore_ret_codes:
            raise subprocess.CalledProcessError(
                retcode,
                shell_process.args,
                )
        #not a sucsessfull execution but an alowed exit code
        #append the error to the output
        if not sucsess(retcode):
            output += shell_process.stderr.read()


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

    if retcode and retcode not in ignore_ret_codes:
        raise subprocess.CalledProcessError(
            retcode,
            process.args,
        )
