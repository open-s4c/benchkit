# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pathlib
import shlex
import subprocess
import sys
from multiprocessing import Process, Queue
from typing import Dict, Iterable, List, Optional

from benchkit.shell.commandAST import command as makecommand
from benchkit.shell.commandAST.nodes.commandNodes import CommandNode
from benchkit.shell.commandAST.visitor import getString


def shell_out_new(
    command: str | List[str] | CommandNode,
    std_input: str | None = None,
    redirect_stderr_to_stdout: bool = True,  # New feature
    current_dir: Optional[pathlib.Path | os.PathLike | str] = None,
    environment: None | Dict[str, str] = None,
    # shell: bool = False, Support REMOVED
    print_command: bool = True,  # TEMPORARALY not suported
    print_output: bool = False,
    print_env: bool = True,  # TEMPORARALY not suported
    print_curdir: bool = True,  # TEMPORARALY not suported
    print_shell_cmd: bool = False,  # TEMPORARALY not suported
    print_file_shell_cmd: bool = True,  # TEMPORARALY not suported
    timeout: Optional[int] = None,
    output_is_log: bool = False,
    ignore_ret_codes: Iterable[int] = (),
    # split_arguments: bool = True, Support REMOVED -> can be achieved in another manner
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
        print_command (bool, optional):
            whether to print the command.
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
            This allows for the usage of commands using things like the pipe symbol,
            use with shell=True for this functionality.
            Defaults to True.

    Raises:
        subprocess.CalledProcessError:
            if the command exited with a non-zero exit code that is not ignored in
            `ignore_ret_codes`.

    Returns:
        str: the output of the shell command that completed successfully.
    """

    # this will run the true command confirming the exit code instead of assuming it
    completedProcess = subprocess.run(["true"], timeout=None)
    sucsess_value = completedProcess.returncode

    def sucsess(value):
        return value == sucsess_value

    # Convert the existing structures over to the tree structure
    commandTree: CommandNode
    if isinstance(command, str):
        commandTree = makecommand.command(command)
    elif isinstance(command, list):
        commandTree = makecommand.command(shlex.join(command))
    elif isinstance(command, CommandNode):
        commandTree = command
    else:
        raise TypeError(
            f"Shell out was called with a command of type {type(command)},"
            "this is unexpected and not suported"
        )

    # Use the visitor patterns to convert our tree to an executable string
    stringCommand = getString(commandTree)


    def try_conventing_bystring_to_readable_characters(bytestring):
        try:
            bytestring = bytestring.decode('utf-8')
        except Exception:
            pass
        return bytestring

    def flush_outlines(std_in):
        """
        prints and returns the current content of stdout for a given process
        Args:
            process (Popen):
                process to log
        Returns:
            str: content of stdout.
        """
        outlines = []
        outline = try_conventing_bystring_to_readable_characters(std_in.readline())

        while outline:
            print(outline, end="")
            outlines.append(outline)
            outline = try_conventing_bystring_to_readable_characters(std_in.readline())
        return outlines

    def flush_thread(std_in, std_err, output_queue):
        """
        while process is running will log and store all stdout in real time
        Args:
            output_queue (Queue):
                Queue to write the returned value to
        Returns:
            None
        """
        output_queue.put("".join(flush_outlines(std_in)))

    if redirect_stderr_to_stdout:
        stderr_out = subprocess.STDOUT
    else:
        stderr_out = subprocess.PIPE

    with subprocess.Popen(
        stringCommand,
        shell=True,
        cwd=current_dir,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=stderr_out,
        stdin=subprocess.PIPE,
    ) as shell_process:
        if shell_process.stdin is not None and std_input is not None:
            shell_process.stdin.write(std_input.encode('utf-8'))

        if output_is_log:
            try:

                # logging the process takes two threads since we need to wait for the timeout
                # while logging stdout in real time, to accomplish this we use multiprocessing
                # in combination with error catching to interupt the logging if needed
                output_queue:Queue = Queue()
                logger_process = Process(
                    target=flush_thread,
                    args=(
                        shell_process.stdout,
                        shell_process.stderr,
                        output_queue,
                    ),
                )
                logger_process.daemon = True
                logger_process.start()
                retcode = shell_process.wait(timeout=timeout)
                logger_process.join()
                print(f"retcode seq {retcode}")
                output = output_queue.get()

            except subprocess.TimeoutExpired as err:
                shell_process.kill()
                logger_process.terminate()
                raise err

        else:
            try:
                retcode = shell_process.wait(timeout=timeout)
                if shell_process.stdout is None:
                    output = ""
                else:
                    output = try_conventing_bystring_to_readable_characters(shell_process.stdout.read())
            except subprocess.TimeoutExpired as err:
                shell_process.kill()
                raise err

        # not a sucsessfull execution and not an alowed exit code
        # raise the appropriate error
        if not sucsess(retcode) and retcode not in ignore_ret_codes:
            raise subprocess.CalledProcessError(
                retcode,
                shell_process.args,
            )

    if print_output and not output_is_log:
        if "" != output.strip():
            print("[OUT]")
            print(output.strip())

    assert isinstance(output, str)
    return output
