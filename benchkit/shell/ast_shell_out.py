# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pathlib
import shlex
import subprocess

from typing import Dict, Iterable, List, Optional

from benchkit.shell.CommunicationLayer.hooks.hook import IOWriterHook
from benchkit.shell.commandAST import command as makecommand
from benchkit.shell.commandAST.nodes.commandNodes import CommandNode
from benchkit.shell.commandAST.visitor import getString
from benchkit.shell.CommunicationLayer.hooks.basic_hooks import (
    logger_hook,
    std_out_result_void_err,
    void_hook,
)
from benchkit.shell.CommunicationLayer.IO_stream import (
    ReadableIOStream,
)
from benchkit.shell.CommunicationLayer.OutputObject import sshOutput


def convert_command_to_ast(command: str | List[str] | CommandNode) -> CommandNode:
    if isinstance(command, str):
        command_tree = makecommand.command(command)
    elif isinstance(command, list):
        command_tree = makecommand.command(shlex.join(command))
    elif isinstance(command, CommandNode):
        command_tree = command
    else:
        raise TypeError(
            f"Shell out was called with a command of type {type(command)},"
            "this is unexpected and not suported"
        )
    return command_tree


def shell_out_new(
    command_tree: CommandNode,
    std_input: Optional[ReadableIOStream] = None,
    current_dir: Optional[pathlib.Path | os.PathLike | str] = None,
    environment: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    output_is_log: bool = False,
    ignore_ret_codes: Optional[Iterable[int]] = None,
    print_command_start: bool = True,  # Reworked feature
    success_value: int = 0,  # New feature
    redirect_stderr_to_stdout: bool = True,  # New feature
    run_in_background=False,  # New feature
    # Some of the visual printing are not supported.
    # Will probably swap over to a file based logging
    # system for these larger amounts of additionaly information
    print_env: bool = True,  # TEMPORARALY not suported
    print_curdir: bool = True,  # TEMPORARALY not suported
    print_shell_cmd: bool = False,  # TEMPORARALY not suported
    print_file_shell_cmd: bool = True,  # TEMPORARALY not suported
) -> bytes:
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
    if ignore_ret_codes is None:
        ignore_ret_codes = (success_value,)
    else:
        ignore_ret_codes += (success_value,)

    # Use the visitor patterns to convert our tree to an executable string
    command_string = getString(command_tree)

    #TODO: I dont like this should be a hook so we can manipulate when this is done
    stderr_out = subprocess.PIPE
    if redirect_stderr_to_stdout:
        stderr_out = subprocess.STDOUT

    shell_process = subprocess.Popen(
        # why exec:
        # we want to be able to use shell=True
        # however this would make the shell the pid of the subprocess
        # by using exec we can get make the command take over the pid of the shell
        # this only works for POSIX (fixable for non posix by finding child)
        f"exec {command_string}",
        shell=True,
        cwd=current_dir,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=stderr_out,
        stdin=subprocess.PIPE,
    )

    # TODO:move to higher abstraction
    # if print_command_start:
    #     print(f"\033[32m[START | {command_string}]\033[0m")
    try:
        # hookfunction to write a ReadableIOStream to stdin
        # TODO: check if we can turn this into a deafault external hook (shell_process is accesed by scope)
        def pasalong(input_stream:ReadableIOStream,_) -> None:
            if shell_process.stdin is not None:
                outline = input_stream.read(1)
                while outline:
                    shell_process.stdin.write(outline)
                    shell_process.stdin.flush()
                    outline = input_stream.read(1)

        # feeding the standard input into the command
        if std_input is not None:
            hook = IOWriterHook(pasalong)
            # TODO: replace std_input by hooked input
            hook.start_hook_function(std_input)
        elif shell_process.stdin is not None:
            shell_process.stdin.close()

        command_output = sshOutput(shell_process.stdout, shell_process.stderr)

        for hk in outhooks:
            command_output = hk.attatch(command_output)

        void_hook().attatch(command_output)

        if shell_process.stdout is not None:
            shell_process.stdout.close()
        if shell_process.stderr is not None:
            shell_process.stderr.close()
        if shell_process.stdin is not None:
            shell_process.stdin.close()

        return CommandProcess(shell_process,timeout)




        if output_is_log:
            command_output = logger_hook(command_string).attatch(command_output)
        try:
            if run_in_background:
                void_hook().attatch(command_output)
                # TODO: run_in_background makes it incompatible with timeout, this is fixable
                # shell_process.wait(timeout=timeout)
                print("pa")
                return b""
            else:
                output_hook_object, voiding_result_hook = std_out_result_void_err()
                voiding_result_hook.attatch(command_output)
                retcode = shell_process.wait(timeout=timeout)
                output = output_hook_object.get_result()

        except subprocess.TimeoutExpired as err:
            # killing this will send eof to and end the hooks aswell
            shell_process.kill()
            raise err


        # not a sucsessfull execution and not an alowed exit code
        # raise the appropriate error
        if retcode not in ignore_ret_codes:
            raise subprocess.CalledProcessError(
                retcode,
                shell_process.args,
            )

        return output
    finally:
        # If something goes wrong we try to clean up after ourself
        # This can happen for example if we recieve a signal while waiting on an output
        # TODO: dumbass this does not work with the "run_in_background argument"
        pass
        # try:
        #     if shell_process.stderr is not None:
        #         shell_process.stderr.close()
        #     if shell_process.stdout is not None:
        #         shell_process.stdout.close()
        # finally:
        #     shell_process.terminate()
        #     # Wait allows the Popen process to cleanly terminate
        #     shell_process.wait(1)
