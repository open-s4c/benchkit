from multiprocessing import Process, Queue
from subprocess import Popen


class CommandProcess():
    def __init__(self,popen_object,timeout):
        self.popen_object = popen_object
        self.timeout = timeout
        self.__retcode_queue = Queue()
        self.retcode = None
        self.wait_async()

    @staticmethod
    def wait_func(subprocess:Popen,queue:Queue,timeout:int):
        retcode = subprocess.wait(timeout)
        queue.put(retcode)


    def wait_async(self):
        Process(target=self.wait_func,args=(self.popen_object,self.__retcode_queue))

    def get_return_code(self):
        if self.retcode:
            return self.retcode
        self.retcode = self.__retcode_queue.get()