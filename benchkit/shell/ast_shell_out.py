# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pathlib
import shlex
import subprocess

from typing import Dict, Iterable, List, Optional

from benchkit.shell.CommunicationLayer.CommandProcess import CommandProcess
from benchkit.shell.CommunicationLayer.hooks.hook import IOHook, IOWriterHook, OutputHook
from benchkit.shell.commandAST import command as makecommand
from benchkit.shell.commandAST.nodes.commandNodes import CommandNode
from benchkit.shell.commandAST.visitor import getString
from benchkit.shell.CommunicationLayer.hooks.basic_hooks import (
    logger_hook,
    std_out_result_void_err,
    void_hook,
)
from benchkit.shell.CommunicationLayer.IO_stream import (
    EmptyIOStream,
    ReadableIOStream,
    WritableIOStream,
)
from benchkit.shell.CommunicationLayer.OutputObject import sshOutput

def execute_command(

    # needed for starting the command
    command: List[str],
    current_dir: Optional[pathlib.Path | os.PathLike | str] = None,
    environment: Optional[Dict[str, str]] = None,

    # needed for construction of output
    timeout: Optional[int] = None,
    ignore_ret_codes: Optional[Iterable[int]] = None,
    success_value: int = 0,  # New feature

    std_input: Optional[ReadableIOStream] = None,
    ordered_input_hooks:Optional[List[IOHook]] = None,
    ordered_output_hooks:Optional[List[OutputHook]] = None,


    # Some of the visual printing are not supported.
    # Will probably swap over to a file based logging
    # system for these larger amounts of additionaly information


    print_command_start: bool = True,  # Reworked feature
    redirect_stderr_to_stdout: bool = True,  # New feature
    run_in_background=False,  # New feature
    output_is_log: bool = False,

    print_env: bool = True,  # TEMPORARALY not suported
    print_curdir: bool = True,  # TEMPORARALY not suported
    print_shell_cmd: bool = False,  # TEMPORARALY not suported
    print_file_shell_cmd: bool = True,  # TEMPORARALY not suported
) -> CommandProcess:

    # Use the visitor patterns to convert our tree to an executable string

    # command_string.insert(0, "exec")

    shell_process = subprocess.Popen(
        # why exec:
        # we want to be able to use shell=True
        # however this would make the shell the pid of the subprocess
        # by using exec we can get make the command take over the pid of the shell
        # this only works for POSIX (fixable for non posix by finding child)
        command,
        # shell=True,
        cwd=current_dir,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )

    # TODO:move to higher abstraction
    # if print_command_start:
    #     print(f"\033[32m[START | {command_string}]\033[0m")
    try:
        if ordered_input_hooks is not None:
            if std_input is None:
                std_input = EmptyIOStream()
            for inhook in ordered_input_hooks:
                inhook.start_hook_function(std_input)
                std_input = inhook.get_outgoing_io_stream()


        # hookfunction to write a ReadableIOStream to stdin
        # TODO: check if we can turn this into a deafault external hook (shell_process is accesed by scope)
        def pasalong(input_stream:ReadableIOStream,_) -> None:
            if shell_process.stdin is not None:
                outline = input_stream.read(1)
                while outline:
                    shell_process.stdin.write(outline)
                    shell_process.stdin.flush()
                    outline = input_stream.read(1)
                shell_process.stdin.close()


        # feeding the standard input into the command
        if std_input is not None:
            hook = IOWriterHook(pasalong)
            # TODO: replace std_input by hooked input
            hook.start_hook_function(std_input)
        if shell_process.stdin is not None:
            shell_process.stdin.close()

        command_output = sshOutput(shell_process.stdout, shell_process.stderr)

        if ordered_output_hooks is not None:
            for outhook in ordered_output_hooks:
                command_output = outhook.attatch(command_output)

        # close all the main thread file descriptors
        if shell_process.stdout is not None:
            shell_process.stdout.close()
        if shell_process.stderr is not None:
            shell_process.stderr.close()
        if shell_process.stdin is not None:
            shell_process.stdin.close()

        return CommandProcess(shell_process,command_output,timeout,success_value)




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
