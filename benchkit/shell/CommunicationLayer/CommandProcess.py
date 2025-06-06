
from __future__ import annotations  # Otherwise Queue comlains about typing

from multiprocessing import Queue
from subprocess import Popen, TimeoutExpired
from threading import Thread
from time import sleep
from typing import Optional

from benchkit.shell.CommunicationLayer.OutputObject import Output


class CommandProcess():
    def __init__(self,popen_object:Popen,output:Output,timeout:Optional[int],success_value:int):
        self.__popen_object:Popen = popen_object
        self.__output:Output = output
        self.__timeout:Optional[int] = timeout
        self.__retcode_queue:Queue[int] = Queue()
        self.success_value:int = success_value
        self.retcode:Optional[int] = None
        self.process:Thread = self.__wait_async()

    #TODO: ignore ret codes and succes value and errors

    @staticmethod
    def wait_func(subprocess:Popen,queue:Queue,timeout:Optional[int]) -> None:
        try:
            retcode = subprocess.wait(timeout)
            queue.put(retcode)
        except TimeoutExpired:
            #TODO: we can add some form of logging here to warn the user if something went wrong
            subprocess.terminate()
            queue.put(-1)

    def __wait_async(self) -> Thread:
        waiting_thread = Thread(target=self.wait_func,args=(self.__popen_object,self.__retcode_queue,self.__timeout))
        waiting_thread.start()
        return waiting_thread

    def get_output(self) -> Output:
        return self.__output

    # TODO: throw error when needed instead of the -1
    def get_return_code(self) -> int:
        print(f'poll main: {self.__popen_object.poll()}')
        if self.retcode:
            return self.retcode
        self.process.join()
        self.retcode = self.__retcode_queue.get()
        return self.retcode

    # TODO: check how this interacts with ssh
    # THIS DOES NOT SEND IT TO THE RIGHT ONE -> move abstraction higher
    def signal(self,signalcode:int) -> None:
        self.__popen_object.send_signal(signalcode)
        # self.__popen_object.wait(1)