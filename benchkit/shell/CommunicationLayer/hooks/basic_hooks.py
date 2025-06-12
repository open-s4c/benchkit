# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from __future__ import annotations  # Otherwise Queue comlains about typing

from multiprocessing import Queue
from typing import Any

from benchkit.shell.CommunicationLayer.hooks.hook import (
    IOReaderHook,
    IOResultHook,
    IOWriterHook,
    OutputHook,
)
from benchkit.shell.CommunicationLayer.IO_stream import (
    ReadableIOStream,
    WritableIOStream,
    try_converting_bystring_to_readable_characters,
)


def create_voiding_result_hook() -> IOResultHook:
    def hook_function(
        input_object: ReadableIOStream, _: WritableIOStream, result_queue: Queue[Any]
    ):
        # we do not write to the out stream thus this is "voiding"
        outlines: bytes = b""
        outline = input_object.read(10)
        while outline:
            outlines += outline
            outline = input_object.read(10)
        result_queue.put(outlines)

    return IOResultHook(hook_function)


def create_stream_line_logger_hook(formating_string: str) -> IOReaderHook:
    def hook_function_line(input_object: ReadableIOStream):
        byt = input_object.read_line()
        while byt:
            print(
                formating_string.format(f"{try_converting_bystring_to_readable_characters(byt)}"),
                end="",
            )
            byt = input_object.read_line()

    return IOReaderHook(hook_function_line)


# TODO: Voiding can be done be done better but this will do for now
# problem: if there are hooks on the output they will wait for input still
# can be resolved by making use of EmptyIOStream
# Needs to be done on a higher level than hooks
def void_input(input_object: ReadableIOStream, _: WritableIOStream):
    outline = input_object.read(10)
    while outline:
        outline = input_object.read(10)


def logger_line_hook(outformat: str, errformat: str):
    return OutputHook(
        create_stream_line_logger_hook(outformat),
        create_stream_line_logger_hook(errformat),
    )


def void_hook():
    return OutputHook(IOWriterHook(void_input), IOWriterHook(void_input))


def std_out_result_void_err():
    output_hook_object = create_voiding_result_hook()

    voiding_result_hook = OutputHook(output_hook_object, IOWriterHook(void_input))

    return (output_hook_object, voiding_result_hook)
