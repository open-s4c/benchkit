# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from __future__ import annotations  # Otherwise Queue comlains about typing

from abc import ABC, abstractmethod
from multiprocessing import Process, Queue
from threading import Thread
from typing import Any, Callable, Optional

from benchkit.shell.command_execution.io.stream import (
    EmptyIOStream,
    PipeIOStream,
    ReadableIOStream,
    WritableIOStream,
)
from benchkit.shell.command_execution.io.output import Output


class IOHook(ABC):
    """basic interface that each hook needs to implement"""
    def __init__(self,name:str):
        self._output = PipeIOStream()
        self._stream_duplicate = PipeIOStream()
        self.name=name

    @abstractmethod
    def start_hook_function(self, input_stream: ReadableIOStream) -> None:
        pass

    def get_outgoing_io_stream(self) -> ReadableIOStream:
        return self._output


class IOWriterHook(IOHook):
    """Hook that expects a function of the form Callable[[ReadableIOStream, PipeIOStream]
       intended as a general purpouse stream manupulator"""

    def __init__(self, hook_function: Callable[[ReadableIOStream, PipeIOStream], None], name:Optional[str] = None):
        self.hook_function = hook_function
        if not name:
            name = self.hook_function.__name__
        super().__init__(name)

    def start_hook_function(self, input_stream: ReadableIOStream) -> None:
        # A process is spawned to keep the hookfunction running on the stream
        p = Thread(
            target=self.hook_function,
            args=(input_stream, self._output),
            name=self.name,
        )
        p.start()

        # Close the file descriptor of the main thread, the one from the process will still be alive


class IOReaderHook(IOHook):

    def __init__(self, hook_function: Callable[[ReadableIOStream], None], name:Optional[str] = None):
        self.hook_function = hook_function
        if not name:
            name = self.hook_function.__name__
        super().__init__(name)

    @staticmethod
    def __pas_along_original_stream(
        input_stream: ReadableIOStream, output1_stream: WritableIOStream, output2_stream: WritableIOStream
    ):
        data = input_stream.read(1)
        while data:
            output1_stream.write(data)
            output2_stream.write(data)
            data = input_stream.read(1)

    def start_hook_function(self, input_stream: ReadableIOStream) -> None:

        # A process is spawned to duplicate the input stream for the reading function
        duplication_process = Thread(
            target=self.__pas_along_original_stream,
            args=(
                input_stream,
                self._output,
                self._stream_duplicate,
            ),
            name=self.name + " pasalong",
        )

        # A process is spawned to keep the hookfunction running on the stream
        reader_hook_process = Thread(
            target=self.hook_function,
            args=(self._stream_duplicate,),
            name=self.name,
        )

        duplication_process.start()
        reader_hook_process.start()
        # Close the file descriptor of the main thread, the one from the process will still be alive


class IOResultHook(IOHook):
    """Hook that expects a function of the form
       Callable[[ReadableIOStream, PipeIOStream, Queue[Any]]
       can be used as a writer hook with the added functionality of
       being being able to use the queue as output"""
    def __init__(self, hook_function: Callable[[ReadableIOStream, PipeIOStream, Queue[Any]], None], name:Optional[str] = None):
        self.__queue: Queue[Any] = Queue()
        self.hook_function = hook_function
        if not name:
            name = self.hook_function.__name__
        super().__init__(name)

    def start_hook_function(self, input_stream: ReadableIOStream) -> None:
        p = Thread(
            target=self.hook_function,
            args=(input_stream, self._output, self.__queue),
            name=self.name,
        )
        p.start()

        # Close the file descriptor of the main thread, the one from the process will still be alive

    def get_result(self) -> Any:
        return self.__queue.get()


class OutputHook:
    def __init__(self, std_out_hook: IOHook | None, std_err_hook: IOHook | None):
        self._std_out_hook = std_out_hook
        self._std_err_hook = std_err_hook

    def attatch(self, output: Output) -> Output:
        """attatch the hooks to the IOStreams or pass them allong if there is no hook"""
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
    def __init__(self) -> None:
        self.std_out = PipeIOStream()
        self._std_err_hook:IOWriterHook = IOWriterHook(self.__mergehookfunction)
        self._std_out_hook:IOWriterHook = IOWriterHook(self.__mergehookfunction)

    def __mergehookfunction(self, input_object: ReadableIOStream, _: WritableIOStream):
        outline = input_object.read_line()
        while outline:
            self.std_out.write(outline)
            outline = input_object.read_line()

    def attatch(self, output: Output) -> Output:
        self._std_err_hook.start_hook_function(output.std_out)
        self._std_out_hook.start_hook_function(output.std_err)

        return Output(self.std_out, EmptyIOStream())
