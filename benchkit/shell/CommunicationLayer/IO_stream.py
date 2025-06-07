# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
from abc import ABC, abstractmethod
from typing import IO

class WritableIOStream(ABC):
    @abstractmethod
    def write(self, bytes_to_write: bytes) -> None:
        pass

    @abstractmethod
    def endWriting(self) -> None:
        pass



class ReadableIOStream(ABC):
    """interface to communicate with command output on all platforms,
    functions are  due to compatibility"""

    def __init__(self):
        self.__buffer: bytes = b""

    @abstractmethod
    def _read_bytes(self, amount_of_bytes: int) -> bytes:
        pass

    def read(self, amount_of_bytes: int) -> bytes:
        """reads at most amount_of_bytes from the available stdout"""
        if self.__buffer:
            ret = self.__buffer
            self.__buffer = b""
            return ret
        return self._read_bytes(amount_of_bytes)

    def read_line(self) -> bytes:
        byt = self.read(10)
        while byt:
            sp = byt.split(b"\n", 1)
            if len(sp) > 1:
                self.__buffer = sp[1]
                return sp[0] + b"\n"
            byt += self.read(10)
        return byt


class SshIOStream(ReadableIOStream):
    def __init__(self, stream: IO[bytes] | None):
        self.__stream = stream
        super().__init__()

    def _read_bytes(self, amount_of_bytes: int) -> bytes:
        if self.__stream:
            return self.__stream.read(amount_of_bytes)
        return b's'

class StringIOStream(ReadableIOStream):
    def __init__(self,string:str,encoding:str="utf-8"):
        self.byte_string = string.encode(encoding)
        self.length = len(self.byte_string)
        self.index = 0
        super().__init__()

    def _read_bytes(self, amount_of_bytes:int):
        if self.index + amount_of_bytes < self.length:
            return_byte_string = self.byte_string[self.index:self.index + amount_of_bytes]
            self.index += amount_of_bytes
            return return_byte_string
        else:
            return_byte_string = self.byte_string[self.index:]
            self.index=self.length
            return return_byte_string



class EmptyIOStream(ReadableIOStream):
    def __init__(self):
        super().__init__()

    def  _read_bytes(self, amount_of_bytes:int):
        return b''


class PipeIOStream(ReadableIOStream,WritableIOStream):
    """A way to create a fileStream that can be used as a CommandOutput by other functions"""

    def __init__(self) -> None:
        self.reader, self.writer = os.pipe()
        os.set_inheritable(self.reader, True)
        os.set_inheritable(self.writer, True)
        super().__init__()

    def write(self, bytes_to_write: bytes) -> None:
        os.write(self.writer, bytes_to_write)

    def endWriting(self) -> None:
        os.close(self.writer)

    def _read_bytes(self, amount_of_bytes: int) -> bytes:
        return os.read(self.reader, amount_of_bytes)


def try_converting_bystring_to_readable_characters(bytestring: bytes) -> str | bytes:
    try:
        return bytestring.decode("utf-8")
    except UnicodeDecodeError:
        return bytestring
