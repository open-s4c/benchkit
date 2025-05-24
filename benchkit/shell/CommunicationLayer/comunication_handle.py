# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from io import BufferedReader
import os
from abc import ABC, abstractmethod


class Output(ABC):
    """interface to communicate with command output on all platforms,
    functions are  due to compatibility"""

    def __init__(self):
        self.__bufferd_out:bytes = b''
        self.__bufferd_err:bytes = b''
        self.a = 2


    @abstractmethod
    def _read_bytes_out(self, amount_of_bytes: int) -> bytes:
        pass
    
    @abstractmethod
    def _read_bytes_err(self, amount_of_bytes: int) -> bytes:
        pass

    def readOut(self, amount_of_bytes: int) -> bytes:
        """reads at most amount_of_bytes from the available stdout"""
        if self.__bufferd_out:
            ret = self.__bufferd_out
            self.__bufferd_out = b''
            self.a = 0
            return ret
        self.a += 1
        # print(f'come from buffer non {self.a}')
        return self._read_bytes_out(amount_of_bytes)

    def readErr(self, amount_of_bytes: int) -> bytes:
        """reads at most amount_of_bytes from the available stderr"""
        if self.__bufferd_err:
            ret = self.__bufferd_err
            self.__bufferd_err = b''
            return ret
        return self._read_bytes_err(amount_of_bytes)

    def readOut_line(self) -> bytes:
        byt = self.readOut(10)
        while byt:
            sp = byt.split(b'\n')
            if len(sp) > 1:
                self.__bufferd_out = sp[1]
                return sp[0]
            byt += self.readOut(10)
        return byt

    def readErr_line(self) -> bytes:
        byt = self.readErr(10)
        while byt:
            sp = byt.split(b'\n')
            if len(sp) > 1:
                self.__bufferd_err = sp[1]
                return sp[0]
            byt += self.readErr(10)
        return byt

class SshOutput(Output):
    def __init__(self,out:BufferedReader,err:BufferedReader):
        self.__out = out
        self.__err = err
        super().__init__()

    def _read_bytes_err(self, amount_of_bytes:int) -> bytes:
        return self.__err.read(amount_of_bytes)

    def _read_bytes_out(self, amount_of_bytes:int) -> bytes:
        return self.__out.read(amount_of_bytes)


class WritableOutput(Output):
    """A way to create a fileStream that can be used as a CommandOutput by other functions"""

    def __init__(self) -> None:
        self.readerOut, self.writerOut = os.pipe()
        self.readerErr, self.writerErr = os.pipe()
        os.set_inheritable(self.readerOut,True)
        os.set_inheritable(self.readerErr,True)
        os.set_inheritable(self.writerOut,True)
        os.set_inheritable(self.writerErr,True)
        super().__init__()

    def writeOut(self, bytes_to_write: bytes) -> None:
        os.write(self.writerOut, bytes_to_write)

    def writeErr(self, bytes_to_write: bytes) -> None:
        os.write(self.writerErr, bytes_to_write)

    def endWritingOut(self) -> None:
        os.close(self.writerOut)

    def endWritingErr(self) -> None:
        os.close(self.writerErr)

    def _read_bytes_out(self, amount_of_bytes: int) -> bytes:
        return os.read(self.readerOut, amount_of_bytes)

    def _read_bytes_err(self, amount_of_bytes: int) -> bytes:
        return os.read(self.readerErr, amount_of_bytes)


"""File notes OUTDATED KEPT FOR REFERENCE FOR A BIT

the read function needs verry thourough testing to make sure that all of the edge cases are the same
-> is it blocking when X bytes requested and there are not X bytes available
-> how does it react on reading X bytes when endof file has been reached
-> how does it react when the stream has been closed
=> these need to become documented so that further implementations can follow it

OutClosed has been removed due to there being no way to detect this without
blocking for the local intreface
-> detecting if there is stil data needs to be done manualy in the hooks
  -> if you recieve a b'' no further data will be readable



CommandPassthrough can we fill the buffer and what happens if we do
-> if hooks dont clear it fast enough what will happen
-> test this


"""
