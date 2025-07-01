# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from __future__ import annotations  # Otherwise Queue comlains about typing

from abc import ABC, abstractmethod
from threading import Lock, Thread
from queue import Queue
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
        self.name=name

    @abstractmethod
    def start_hook_function(self, input_stream: ReadableIOStream) -> None:
        pass

    def _start_thread_and_cleanup(self,target,args,name,to_close):
        def _wrap(target,args,to_close:list[WritableIOStream]):
            target(*args)
            for stream in to_close:
                stream.end_writing()

        p = Thread(
            target=_wrap,
            args=(target,args,to_close),
            name=name,
        )

        p.start()



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
        # A thread is spawned to keep the hookfunction running on the stream
        self._start_thread_and_cleanup(self.hook_function,(input_stream, self._output),self.name,[self._output])


class IOReaderHook(IOHook):

    def __init__(self, hook_function: Callable[[ReadableIOStream], None], name:Optional[str] = None):
        self.hook_function = hook_function
        self._stream_duplicate = PipeIOStream()
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

        # A thread is spawned to duplicate the input stream for the reading function
        self._start_thread_and_cleanup(self.__pas_along_original_stream,(
                input_stream,
                self._output,
                self._stream_duplicate,
            ),self.name + " pasalong",[self._output,self._stream_duplicate])

        # A thread is spawned to keep the hookfunction running on the duplicate stream
        self._start_thread_and_cleanup(self.hook_function,(
                self._stream_duplicate,
            ),self.name,[])


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

        self._start_thread_and_cleanup(self.hook_function,
                                       (input_stream, self._output, self.__queue)
                                       ,self.name,[self._output])

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
        # a lock for the out pipe only if released can we clean it up
        self.lock = Lock()
        self.lock.acquire()

        self._std_err_hook:IOWriterHook = IOWriterHook(self.__mergehookfunction,name="merge-hook-err")
        self._std_out_hook:IOWriterHook = IOWriterHook(self.__mergehookfunction_close,name="merge-hook-out")

    def __mergehookfunction(self, input_object: ReadableIOStream, _: WritableIOStream):
        outline = input_object.read_line()
        while outline:
            self.std_out.write(outline)
            outline = input_object.read_line()
        # other thread can clean up the file now
        self.lock.release()

    def __mergehookfunction_close(self, input_object: ReadableIOStream, _: WritableIOStream):
        outline = input_object.read_line()
        while outline:
            self.std_out.write(outline)
            outline = input_object.read_line()
        self.lock.acquire()
        self.std_out.end_writing()

    def attatch(self, output: Output) -> Output:
        self._std_err_hook.start_hook_function(output.std_out)
        self._std_out_hook.start_hook_function(output.std_err)

        return Output(self.std_out, EmptyIOStream())
