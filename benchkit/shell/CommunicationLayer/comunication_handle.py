
from abc import ABC,abstractmethod

import os

class Output(ABC):
    """interface to communicate with command output on all platforms, functions are  due to compatibility"""    
    @abstractmethod
    def readOut(self, amount_of_bytes:int) -> bytes:
        """reads at most amount_of_bytes from the available stdout"""
        pass
    
    @abstractmethod
    def readErr(self, amount_of_bytes:int) -> bytes:
        """reads at most amount_of_bytes from the available stderr"""
        pass
    
    @abstractmethod
    def getReaderFdOut(self) -> int:
        pass
    
    @abstractmethod
    def getReaderFdErr(self) -> int:
        pass

class WritableOutput(Output):
    """A way to create a fileStream that can be used as a CommandOutput by other functions"""
    def __init__(self) -> None:
        self.readerOut, self.writerOut = os.pipe()
        self.readerErr, self.writerErr = os.pipe()

    def writeOut(self, bytes_to_write:bytes) -> None:
        os.write(self.writerOut,bytes_to_write)

    def endWritingOut(self) -> None:
        os.close(self.writerOut)
    
    def readOut(self, amount_of_bytes:int) -> bytes:
        return os.read(self.readerOut, amount_of_bytes)
    
    def getReaderFdOut(self) -> int:
        return self.readerOut
    
    def getWriterFdOut(self) -> int:
        return self.writerOut
    
    def writeErr(self, bytes_to_write:bytes) -> None:
        os.write(self.writerErr,bytes_to_write)

    def endWritingErr(self) -> None:
        os.close(self.writerErr)

    def readErr(self, amount_of_bytes:int) -> bytes:
        return os.read(self.readerErr, amount_of_bytes)
    
    def getReaderFdErr(self) -> int:
        return self.readerErr
    
    def getWriterFdErr(self) -> int:
        return self.writerErr
    


"""File notes OUTDATED KEPT FOR REFERENCE FOR A BIT

the read function needs verry thourough testing to make sure that all of the edge cases are the same
-> is it blocking when X bytes requested and there are not X bytes available
-> how does it react on reading X bytes when endof file has been reached
-> how does it react when the stream has been closed
=> these need to become documented so that further implementations can follow it

OutClosed has been removed due to there being no way to detect this withou blocking for the local intreface
-> detecting if there is stil data needs to be done manualy in the hooks
  -> if you recieve a b'' no further data will be readable 

  

CommandPassthrough can we fill the buffer and what happens if we do 
-> if hooks dont clear it fast enough what will happen
-> test this


"""