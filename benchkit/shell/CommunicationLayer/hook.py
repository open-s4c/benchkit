from __future__ import annotations #Otherwise Queue comlains about typing
from abc import ABC, abstractmethod
from multiprocessing import Process, Queue
from typing import Callable
from benchkit.shell.CommunicationLayer.comunication_handle import Output, WritableOutput



# change -> this should be a "result hook" 
#           -> Hook should be a pastrough hook
#           -> Hook should have getPassthrough() removed
# This would allow for composition where every hook needs to end in a result hook (deafault is voiding it -> would be async)

class OutputBuffer:
    def __init__(self,out:Output) -> None:
        self.queue:Queue[bytes]=Queue()
        self.out=out

        logger_process = Process(
                    target=self.result_thread,
                    args=(
                        self.out,
                        self.queue,
                    ),
                )
        logger_process.start()

    @staticmethod
    def result_thread(out:Output,output_queue:Queue[bytes]) -> None:
        outlines:bytes = b''
        outline = out.readOut(10)
        while outline:
            outlines += outline
            outline = out.readOut(10)
        output_queue.put(outlines)

    def get_result(self) -> bytes:
        output = self.queue.get()
        return output


class Hook(ABC):
    @abstractmethod
    def startHookFunction(self,comandOutput:Output) -> None:
        pass

    @abstractmethod
    def getPassthrough(self) -> WritableOutput:
        pass

class WriterHook(Hook):
    def __init__(self,hookFunction:Callable[[Output,WritableOutput],None]):
        self.__output = WritableOutput()
        self.hookFunction = hookFunction

    def startHookFunction(self,comandOutput:Output):
        p = Process(
            target=self.hookFunction,
            args=(
                comandOutput,
                self.__output
            )
        )
        p.start()
        self.__output.endWritingErr()
        self.__output.endWritingOut()

    def getPassthrough(self):
        return self.__output



class ReaderHook(Hook):

    @staticmethod
    def pasAlongStdOut(input:Output ,output:WritableOutput,splitof:WritableOutput,void_stdout:bool):
        output.endWritingErr()
        splitof.endWritingErr()

        while True:
            data = input.readOut(1)
            if not data:
                break
            output.writeOut(data)
            if not void_stdout:
                splitof.writeOut(data)
        output.endWritingOut()

        if not void_stdout:
            splitof.endWritingOut()

    @staticmethod
    def pasAlongStdErr(input:Output ,output:WritableOutput,splitof:WritableOutput,void_stderr:bool):

        output.endWritingOut()
        splitof.endWritingOut()

        while True:
            data = input.readErr(1)
            if not data:
                break
            output.writeErr(data)
            if not void_stderr:
                splitof.writeErr(data)
        output.endWritingErr()

        if not void_stderr:
            splitof.endWritingErr()

    def __init__(self,hookFunction:Callable[[Output],None],voidStdOut:bool=False,voidStdErr:bool=False):
        self.__output = WritableOutput()
        self.__splitof = WritableOutput()
        self.hookfunction = hookFunction
        self.__voidStdErr = voidStdErr
        self.__voidStdOut = voidStdOut


    @staticmethod
    def hookwrap(input:WritableOutput,hookfunction:Callable[[Output],None]):

        input.endWritingOut()
        input.endWritingErr()
        hookfunction(input)

    def startHookFunction(self,comandOutput:Output):
        p1 = Process(
            target=self.pasAlongStdOut,
            args=(
                comandOutput,
                self.__output,
                self.__splitof,
                self.__voidStdOut
            )
        )
        p2 = Process(
            target=self.pasAlongStdErr,
            args=(
                comandOutput,
                self.__output,
                self.__splitof,
                self.__voidStdErr
            )
        )
        p3 = Process(
            target=self.hookwrap,
            args=(
                self.__splitof,
                self.hookfunction
            )
        )
        p1.start()
        p2.start()
        p3.start()
        self.__output.endWritingErr()
        self.__output.endWritingOut()
        self.__splitof.endWritingErr()
        self.__splitof.endWritingOut()

    def getPassthrough(self):
        return self.__output

"""
file notes
voiding something for the reader function can be done in a more efficient method,
we could create an empty passthrouh for the splitof part and just replace the stdOut in the __output
would need to check if this is a clean solution or more of a hack
the current implementation is consisten and 'clean' albe it with a lot of overhead


TODO implement the voiding of certain streams for the writer hooks
this makes it less likely people will make mistakes by ignoring streams and blocking

TODO implement passtrough of certian streams for writer hooks
this makes it less likely people will make mistakes by ignoring streams and blocking

"""
