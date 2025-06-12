# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from __future__ import annotations  # Otherwise Queue comlains about typing

from abc import ABC, abstractmethod
from multiprocessing import Process, Queue
from typing import Any, Callable

from benchkit.shell.CommunicationLayer.IO_stream import (
    EmptyIOStream,
    PipeIOStream,
    ReadableIOStream,
    WritableIOStream,
)
from benchkit.shell.CommunicationLayer.OutputObject import Output


class IOHook(ABC):
    def __init__(self):
        self._output = PipeIOStream()

    @abstractmethod
    def start_hook_function(self, input_stream: ReadableIOStream) -> None:
        pass

    def get_outgoing_io_stream(self) -> ReadableIOStream:
        return self._output


class IOWriterHook(IOHook):
    def __init__(self, hook_function: Callable[[ReadableIOStream, PipeIOStream], None]):
        self.hook_function = hook_function
        self.__name = self.hook_function.__name__
        super().__init__()

    def start_hook_function(self, input_stream: ReadableIOStream) -> None:
        p = Process(
            target=self.hook_function,
            args=(input_stream, self._output),
            name=self.__name,
            daemon=True,
        )
        p.start()

        # Close the file descriptor of the main thread, the one from the process will still be alive
        self._output.endWriting()


class IOReaderHook(IOHook):

    def __init__(self, hook_function: Callable[[ReadableIOStream], None]):
        self.hook_function = hook_function
        self._stream_duplicate = PipeIOStream()
        self.__name = self.hook_function.__name__
        super().__init__()

    @staticmethod
    def __pas_along_original_stream(
        input_stream: ReadableIOStream, output1_stream: PipeIOStream, output2_stream: PipeIOStream
    ):
        while True:
            data = input_stream.read(1)
            if not data:
                break
            output1_stream.write(data)
            output2_stream.write(data)
        output1_stream.endWriting()
        output2_stream.endWriting()

    def start_hook_function(self, input_stream: ReadableIOStream) -> None:
        duplication_process = Process(
            target=self.__pas_along_original_stream,
            args=(
                input_stream,
                self._output,
                self._stream_duplicate,
            ),
            name=self.__name + " pasalong",
            daemon=True,
        )
        reader_hook_process = Process(
            target=self.hook_function,
            args=(self._stream_duplicate,),
            name=self.__name,
            daemon=True,
        )

        duplication_process.start()
        # Close the file descriptor of the main thread, the one from the process will still be alive
        self._output.endWriting()
        self._stream_duplicate.endWriting()
        reader_hook_process.start()


class IOResultHook(IOHook):
    def __init__(self, hook_function: Callable[[ReadableIOStream, PipeIOStream, Queue[Any]], None]):
        self.__queue: Queue[Any] = Queue()
        self.hook_function = hook_function
        self.__name = self.hook_function.__name__
        super().__init__()

    def start_hook_function(self, input_stream: ReadableIOStream) -> None:
        p = Process(
            target=self.hook_function,
            args=(input_stream, self._output, self.__queue),
            name=self.__name,
            daemon=True,
        )
        p.start()

        # Close the file descriptor of the main thread, the one from the process will still be alive
        self._output.endWriting()

    def get_result(self) -> Any:
        return self.__queue.get()


class OutputHook:
    def __init__(self, std_out_hook: IOHook | None, std_err_hook: IOHook | None):
        self._std_out_hook = std_out_hook
        self._std_err_hook = std_err_hook

    def attatch(self, output: Output) -> Output:
        std_out = output.std_out
        std_err = output.std_err
        if self._std_out_hook:
            self._std_out_hook.start_hook_function(output.std_out)
            std_out = self._std_out_hook.get_outgoing_io_stream()
        if self._std_err_hook:
            self._std_err_hook.start_hook_function(output.std_err)
            std_err = self._std_err_hook.get_outgoing_io_stream()
        return Output(std_out, std_err)


class MergeErrToOut(OutputHook):
    def __init__(self):
        self.std_out = PipeIOStream()

    def mergehookfunction(self, input_object: ReadableIOStream, _: WritableIOStream):
        outline = input_object.read_line()
        while outline:
            self.std_out.write(outline)
            outline = input_object.read_line()

    def attatch(self, output: Output) -> Output:
        stdout_hook = IOWriterHook(self.mergehookfunction)
        stderr_hook = IOWriterHook(self.mergehookfunction)
        stdout_hook.start_hook_function(output.std_out)
        stderr_hook.start_hook_function(output.std_err)
        self.std_out.endWriting()

        return Output(self.std_out, EmptyIOStream())
