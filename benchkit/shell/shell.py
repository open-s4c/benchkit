# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interactions with a shell.
"""

import shlex
import signal
import subprocess
import sys
from typing import Iterable, List, Optional

from benchkit.shell.command_execution.execute import execute_command
from benchkit.shell.command_execution.command_process import CommandProcess
from benchkit.shell.command_execution.io.hooks.basic_hooks import (
    logger_line_hook,
    std_out_result_void_err,
    void_hook,
    void_input,
)
from benchkit.shell.command_execution.io.hooks.hook import (
    IOWriterHook,
    MergeErrToOut,
    OutputHook,
)
from benchkit.shell.command_execution.io.stream import (
    EmptyIOStream,
    PipeIOStream,
    ReadableIOStream,
    StringIOStream,
)
from benchkit.shell.utils import get_args, print_header
from benchkit.utils.types import Command, Environment, PathType

USE_NEW_SHELL = True

def split_on_pipe(sub_commands:List[str]):
    full_list:List[List[str]] = []
    sub_command:List[str] = []
    for s in sub_commands:
        if s == "|":
            full_list.append(sub_command)
            sub_command = []
        else:
            sub_command.append(s)
    full_list.append(sub_command)
    return full_list



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
    if USE_NEW_SHELL:
        # create a list for all processes that will be run
        processes: List[CommandProcess] = []

        # no input posible in the begining so we create an empty stream for the first command
        input_stream: ReadableIOStream = EmptyIOStream()

        # create a hook for the last process to gather the result of the piped command
        gather_result_object, gather_result_hook = std_out_result_void_err()

        # break our command in pieces in case there are pipes
        command_split = shlex.split(command) if isinstance(command,str) else command
        command_string = command_string = shlex.join(command_split)
        commands = split_on_pipe(command_split)

        if print_command:
                print(f"\033[32m[Full piped command | {command_string}]\033[0m")

        # enumerate all commands and start a process for each of them
        for idx, com in enumerate(commands):
            # break the command for the execution
            command = shlex.split(com) if isinstance(com, str) else com
            command_string = shlex.join(command)

            # TODO: this technicaly is not the deafault but it stays here for demonstration reasons for a bit
            # log each command
            output_hooks: List[OutputHook] = []
            log = logger_line_hook(
                f"\033[34m[OUT | {command_string}]\033[0m" + " {}",
                f"\033[91m[ERR | {command_string}]\033[0m" + " {}",
            )
            output_hooks.append(log)

            if idx == len(commands) - 1:
                # for the last command we merge err and out and gather it
                output_hooks.append(MergeErrToOut())
                output_hooks.append(gather_result_hook)
            else:
                # for all other commands we void error and out will be used by next command
                void_err = OutputHook(None,IOWriterHook(void_input))
                output_hooks.append(void_err)

            # print the command we are about to start
            if print_command:
                print(f"\033[32m[START | {command_string}]\033[0m")
            process = execute_command(
                command=command,
                std_input=input_stream,
                current_dir=current_dir,
                ordered_output_hooks=output_hooks,
                # If ignore_ret_codes is empty we swap it over to None instead
                ignore_ret_codes=ignore_ret_codes if not any(True for _ in ignore_ret_codes) else None,
            )
            # remember the process
            processes.append(process)

            # Link the output stream to the next by making it the input stream
            input_stream = process.get_output().std_out

        # wait for all procces to finish
        for p in processes:
            p.get_return_code()

        return gather_result_object.get_result().decode("utf-8")
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
            text=True,
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
    if USE_NEW_SHELL:
        command = shlex.split(command) if isinstance(command, str) else command
        command_string = shlex.join(command)

        # convert string input to an IOStream
        std_input_io = StringIOStream(std_input) if std_input is not None else None
        output_hooks: List[OutputHook] = []

        # if we need to ignore any error code we just add all of them to the ignore list
        # the overhead of doing this is minimal and it keeps the code cleaner
        if ignore_any_error_code:
            ignore_ret_codes = (x for x in range(256))

        # add hook to log the output of the command
        if output_is_log:
            log = logger_line_hook(
                f"\033[34m[OUT | {command_string}]\033[0m" + " {}",
                f"\033[91m[ERR | {command_string}]\033[0m" + " {}",
            )
            output_hooks.append(log)

        # Print the input string
        if print_input:
            print(f"\033[32m[START | {command_string}]\033[0m")

        # Original implementation considered the error to be part of the output,
        # we merge them together here (done line wise)
        merge = MergeErrToOut()
        output_hooks.append(merge)

        # gather the entire stdout stream into a variable
        output_hook_object, voiding_result_hook = std_out_result_void_err()
        output_hooks.append(voiding_result_hook)

        # this will make sure we clear all our outputs in the end
        # otherwise the command might block
        output_hooks.append(void_hook())

        process = execute_command(
            command=command,
            std_input=std_input_io,
            current_dir=current_dir,
            environment=environment,
            timeout=timeout,
            ordered_output_hooks=output_hooks,
            ignore_ret_codes=ignore_ret_codes,
        )
        # this line is here to check if the program failed
        process.get_return_code()

        # decode to turn bytestream of into the desired string
        # this can fail but is in line with original implementation
        return output_hook_object.get_result().decode("utf-8")

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
        with (
            subprocess.Popen(
                arguments,
                shell=shell,
                cwd=current_dir,
                env=environment,
                stdout=subprocess.PIPE,
            )
            if std_input is None
            else subprocess.Popen(
                arguments,
                shell=shell,
                cwd=current_dir,
                env=environment,
                stdout=subprocess.PIPE,
                stdin=std_input,
                text=True,
            )
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
    if USE_NEW_SHELL:
        # ok so, you can not exit this,
        # you exit the shell you exit the benchmark

        # TODO: workaround: we can add make custom hooks for this function that survive the interupt signal once
        # using try: except Keyinterupt
        #

        command = shlex.split(command) if isinstance(command, str) else command

        # convert string input to an IOStream
        std_input_io = PipeIOStream()
        output_hooks = []

        # add hook to log the output of the command
        log = logger_line_hook(
            "> {}",
            "! {}",
        )
        output_hooks.append(log)

        output_hooks.append(void_hook())

        # Print the input string
        if print_input:
            print(f"\033[32m[START | {shlex.join(command)}]\033[0m")

        process = execute_command(
            command=command,
            std_input=std_input_io,
            current_dir=current_dir,
            environment=environment,
            ordered_output_hooks=output_hooks,
            # If ignore_ret_codes is empty we swap it over to None instead
            ignore_ret_codes=ignore_ret_codes if not any(True for _ in ignore_ret_codes) else None,
        )

        # We want that the first interupt signal
        # goes to the process we are interacting with
        original_sigint_handler = signal.getsignal(signal.SIGINT)

        # def signal_handler(sig, frame):
        #     process.signal(sig)
        #     sys.stdin.close()
        #     signal.signal(signal.SIGINT, original_sigint_handler)

        # signal.signal(signal.SIGINT, signal_handler)

        # use our stdin as the interaction for the process

        try:
            outline = sys.stdin.read(1).encode("utf-8")
            while outline:
                std_input_io.write(outline)
                outline = sys.stdin.read(1).encode("utf-8")
        # The implementation of sigint will error above code
        # This is intended as the exit method
        except Exception:
            pass
        # except KeyboardInterrupt:
        #     pass
        # Cleanly close the input file
        std_input_io.endWriting()

        return None

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
