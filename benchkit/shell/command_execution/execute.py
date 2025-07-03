# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

# Otherwise os.PathLike[Any] complains
from __future__ import annotations

import pathlib
import subprocess
from typing import Dict, Iterable, List, Optional

from benchkit.shell.command_execution.command_process import CommandProcess
from benchkit.shell.command_execution.io.hooks.hook import (
    IOHook,
    IOWriterHook,
    OutputHook,
)
from benchkit.shell.command_execution.io.stream import (
    EmptyIOStream,
    ReadableIOStream,
    WritableIOStream,
)
from benchkit.shell.command_execution.io.output import popen_get_output

def execute_command(
    # needed for starting the command
    command: List[str],
    # This dir can only be a path on the local machine
    current_dir: Optional[pathlib.Path] = None,
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

    process = subprocess.Popen(
        command,
        cwd=current_dir,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    try:
        # 1) manipulate the input stream using the ordered input hooks
        if ordered_input_hooks is not None:
            if std_input is None:
                std_input = EmptyIOStream()
            for inhook in ordered_input_hooks:
                inhook.start_hook_function(std_input)
                std_input = inhook.get_outgoing_io_stream()

        # 2) Write the input to the command
        # hookfunction to write the ReadableIOStream given as input to stdin
        def pasalong(input_stream: ReadableIOStream, _: WritableIOStream) -> None:
            if process.stdin is not None:
                outline = input_stream.read(1)
                while outline:
                    process.stdin.write(outline)
                    process.stdin.flush()
                    outline = input_stream.read(1)
                process.stdin.close()

        if std_input is not None:
            hook = IOWriterHook(pasalong)
            hook.start_hook_function(std_input)
        # if process.stdin is not None:
            # process.stdin.close()

        # 3) manipulate teh output stream using the orderd output hooks
        command_output = popen_get_output(process.stdout, process.stderr)

        if ordered_output_hooks is not None:
            for outhook in ordered_output_hooks:
                command_output = outhook.attatch(command_output)

        # close all the main thread file descriptors
        # if process.stdout is not None:
        #     process.stdout.close()
        # if process.stderr is not None:
        #     process.stderr.close()
        # if process.stdin is not None:
        #     process.stdin.close()

        # 4) construct the object we can use to monitor the process
        return CommandProcess(
            process, command_output, timeout, success_value, ignore_ret_codes
        )

    except Exception:
        # make sure the process is terminated for cleanup
        # TODO: this needs some test cases
        process.terminate()
        process.wait()
        raise
