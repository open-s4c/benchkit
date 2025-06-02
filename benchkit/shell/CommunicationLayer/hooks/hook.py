from __future__ import annotations  # Otherwise Queue comlains about typing

from abc import ABC, abstractmethod
from multiprocessing import Process, Queue
from typing import Any, Callable
from benchkit.shell.CommunicationLayer.IO_stream import IOStream, WritableIOStream
from benchkit.shell.CommunicationLayer.OutputObject import Output

class IOHook(ABC):
    def __init__(self):
        self._output = WritableIOStream()

    @abstractmethod
    def start_hook_function(self, input_stream: IOStream) -> None:
        pass

    def get_outgoing_io_stream(self) -> IOStream:
        return self._output


class IOWriterHook(IOHook):
    def __init__(self, hook_function:Callable[[IOStream,WritableIOStream],None]):
        self.hook_function = hook_function
        super().__init__()

    def start_hook_function(self, input_stream: IOStream) -> None:
        p = Process(target=self.hook_function, args=(input_stream, self._output))
        p.start()

        #Close the file descriptor of the main thread, the one from the process will still be alive
        self._output.endWriting()

class IOReaderHook(IOHook):

    def __init__(self, hook_function:Callable[[IOStream],None]):
        self.hook_function = hook_function
        self._stream_duplicate = WritableIOStream()
        super().__init__()

    @staticmethod
    def __pas_along_original_stream(input_stream:IOStream,output1_stream:WritableIOStream,output2_stream:WritableIOStream):
        while True:
            data = input_stream.read(1)
            if not data:
                break
            output1_stream.write(data)
            output2_stream.write(data)
        output1_stream.endWriting()
        output2_stream.endWriting()



    def start_hook_function(self, input_stream: IOStream) -> None:
        duplication_process = Process(target=self.__pas_along_original_stream, args=(input_stream, self._output,self._stream_duplicate,))
        reader_hook_process = Process(target=self.hook_function,args=(self._stream_duplicate,))

        duplication_process.start()
        #Close the file descriptor of the main thread, the one from the process will still be alive
        self._output.endWriting()
        self._stream_duplicate.endWriting()
        reader_hook_process.start()

class IOResultHook(IOHook):
    def __init__(self, hook_function:Callable[[IOStream,WritableIOStream,Queue],None]):
        self.__queue:Queue[Any] = Queue()
        self.hook_function = hook_function
        super().__init__()

    def start_hook_function(self, input_stream: IOStream) -> None:
        p = Process(target=self.hook_function, args=(input_stream, self._output,self.__queue))
        p.start()

        #Close the file descriptor of the main thread, the one from the process will still be alive
        self._output.endWriting()

    def get_result(self) -> Any:
        return self.__queue.get()





class OutputHook():
    def __init__(self,std_out_hook:IOHook|None,std_err_hook:IOHook|None):
        self._std_out_hook = std_out_hook
        self._std_err_hook = std_err_hook

    def attatch(self,output:Output) -> Output:
        std_out = output.std_out
        std_err = output.std_err
        if self._std_out_hook:
            self._std_out_hook.start_hook_function(output.std_out)
            std_out = self._std_out_hook.get_outgoing_io_stream()
        if self._std_err_hook:
            self._std_err_hook.start_hook_function(output.std_err)
            std_err = self._std_err_hook.get_outgoing_io_stream()
        return Output(
            std_out,
            std_err
        )