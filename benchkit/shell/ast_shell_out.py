# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

# Otherwise os.PathLike[Any] complains
from __future__ import annotations

import os
import pathlib
import subprocess
from typing import Any, Dict, Iterable, List, Optional

from benchkit.shell.CommunicationLayer.CommandProcess import CommandProcess
from benchkit.shell.CommunicationLayer.hooks.hook import (
    IOHook,
    IOWriterHook,
    OutputHook,
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
    # This dir can only be a path on the local machine
    current_dir: Optional[pathlib.Path] = None,

    # TODO: the environment variable will start a process with only these env variables
    # Do we want to add os.environ to this?
    environment: Optional[Dict[str, str]] = None,
    # needed for construction and evaluation of output
    timeout: Optional[int] = None,
    ignore_ret_codes: Optional[Iterable[int]] = None,
    success_value: int = 0,
    # working with the IOStreams of the command
    std_input: Optional[ReadableIOStream] = None,
    ordered_input_hooks: Optional[List[IOHook]] = None,
    ordered_output_hooks: Optional[List[OutputHook]] = None,
) -> CommandProcess:

    if environment is None:
        environment = {}

    shell_process = subprocess.Popen(
        command,
        cwd=current_dir,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    try:
        if ordered_input_hooks is not None:
            if std_input is None:
                std_input = EmptyIOStream()
            for inhook in ordered_input_hooks:
                inhook.start_hook_function(std_input)
                std_input = inhook.get_outgoing_io_stream()

        # hookfunction to write a ReadableIOStream to stdin
        def pasalong(input_stream: ReadableIOStream, _: WritableIOStream) -> None:
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

        return CommandProcess(
            shell_process, command_output, timeout, success_value, ignore_ret_codes
        )

    except Exception:
        # make sure the process is terminated for cleanup
        # TODO: this needs some test cases
        shell_process.terminate()
        shell_process.wait()
        raise
