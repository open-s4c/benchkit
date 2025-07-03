# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
from abc import ABC, abstractmethod
from typing import IO


class WritableIOStream(ABC):
    """Interface to write any form of data that can be made
       compatible by implementing write and end_writing"""

    @abstractmethod
    def write(self, bytes_to_write: bytes) -> None:
        """write bytes to the given IOStream needs to be implemented depending on what it is"""

    @abstractmethod
    def end_writing(self) -> None:
        """signal that the IOStream can be closed"""


class ReadableIOStream(ABC):
    """interface to read from anny form of data that can be made
       compatible by implementing _read_bytes"""

    def __init__(self) -> None:
        self.__buffer: bytes = b""

    @abstractmethod
    def _read_bytes(self, amount_of_bytes: int) -> bytes:
        pass

    def read(self, amount_of_bytes: int) -> bytes:
        """reads at most amount_of_bytes from the available stdout
           returns the current buffer before it attemts to read more bytes"""
        if self.__buffer:
            ret = self.__buffer
            self.__buffer = b""
            return ret
        return self._read_bytes(amount_of_bytes)

    def read_line(self) -> bytes:
        """reads one line overflows into __buffer"""
        byt = self.read(10)
        while byt:
            sp = byt.split(b"\n", 1)
            if len(sp) > 1:
                self.__buffer = sp[1]
                return sp[0] + b"\n"
            byt += self.read(10)
        return byt


class PopenIOStream(ReadableIOStream):
    """Class that can interact with the stdout type objects given by Popen"""
    def __init__(self, stream: IO[bytes]):
        self.__done=False
        self.__stream = stream
        super().__init__()

    def _read_bytes(self, amount_of_bytes: int) -> bytes:
        if self.__done:
            return b''
        if self.__stream:
            r = self.__stream.read(amount_of_bytes)
            if r:
                return r
            self.__done = True
            self.__stream.close()
            return r
        return b""


class StringIOStream(ReadableIOStream):
    """Class to convert a string to an IOStream so they can be interchanged"""
    def __init__(self, string: str, encoding: str = "utf-8"):
        self.byte_string = string.encode(encoding)
        self.length = len(self.byte_string)
        self.index = 0
        super().__init__()

    def _read_bytes(self, amount_of_bytes: int):
        if self.index + amount_of_bytes < self.length:
            return_byte_string = self.byte_string[self.index : self.index + amount_of_bytes]
            self.index += amount_of_bytes
            return return_byte_string
        else:
            return_byte_string = self.byte_string[self.index :]
            self.index = self.length
            return return_byte_string


class EmptyIOStream(ReadableIOStream):
    "Class to create an empty IOStream"
    def __init__(self):
        super().__init__()

    def _read_bytes(self, amount_of_bytes: int):
        return b""


class PipeIOStream(ReadableIOStream, WritableIOStream):
    """A readable and writable IOStream that is used to communicate between hooks mostly"""

    def __init__(self) -> None:
        self.reader, self.writer = os.pipe()
        os.set_inheritable(self.reader, True)
        os.set_inheritable(self.writer, True)
        super().__init__()

    def write(self, bytes_to_write: bytes) -> None:
        os.write(self.writer, bytes_to_write)

    def end_writing(self) -> None:
        os.close(self.writer)

    def _read_bytes(self, amount_of_bytes: int) -> bytes:
        return os.read(self.reader, amount_of_bytes)


def try_converting_bystring_to_readable_characters(bytestring: bytes) -> str | bytes:
    """ function that will try to convert a bytestring to string
        if it fails it will return back the bytestring so nothing is lost"""
    try:
        return bytestring.decode("utf-8")
    except UnicodeDecodeError:
        return bytestring
