# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from multiprocessing import Queue

from benchkit.shell.CommunicationLayer.hooks.hook import (
    IOReaderHook,
    IOResultHook,
    IOWriterHook,
    OutputHook,
)
from benchkit.shell.CommunicationLayer.IO_stream import (
    ReadableIOStream,
    try_converting_bystring_to_readable_characters,
)


def create_voiding_result_hook() -> IOResultHook:
    def hook_function(input_object: ReadableIOStream, _, result_queue: Queue):
        # we do not write to the out stream thus this is "voiding"
        outlines: bytes = b""
        outline = input_object.read(10)
        while outline:
            outlines += outline
            outline = input_object.read(10)
        result_queue.put(outlines)

    return IOResultHook(hook_function)


def create_stream_logger_hook(prefix: str) -> IOReaderHook:
    def hook_function(input_object: ReadableIOStream):
        a = input_object.read_line()
        while a:
            print(f"{prefix} {try_converting_bystring_to_readable_characters(a)!r}\033[0m")
            a = input_object.read_line()

    return IOReaderHook(hook_function)


def void_input(input_object, _):
    outline = input_object.read(10)
    while outline:
        outline = input_object.read(10)


def logger_hook(command_string):
    return OutputHook(
        create_stream_logger_hook(f"\33[34m[OUT | {command_string}]"),
        create_stream_logger_hook(f"\033[91m[ERR | {command_string}]"),
    )


def void_hook():
    return OutputHook(IOWriterHook(void_input), IOWriterHook(void_input))


def std_out_result_void_err():
    output_hook_object = create_voiding_result_hook()

    voiding_result_hook = OutputHook(output_hook_object, IOWriterHook(void_input))

    return (output_hook_object, voiding_result_hook)
