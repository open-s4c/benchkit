# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.

# SPDX-License-Identifier: MIT

from . import CommunicationLayer, SSHCommLayer
from .extensions.status import StatusAware

import re
import time
import types
import serial
import pathlib

from typing import Iterable

from benchkit.utils.types import Command, PathType, Environment


class UARTCommLayer(CommunicationLayer, StatusAware):
    """Communication layer to handle a device through UART."""

    def __init__(
        self,
        port: pathlib.Path,
        baudrate: int = 115200,
        timeout: float = 1.0,
        ps1: str | None = None,
    ):
        super().__init__()

        self._port: pathlib.Path = port
        self._baudrate: int = baudrate
        self._timeout: float = timeout
        self._is_shell: bool = False
        self._ps1: str | None = ps1

        self._con: serial.Serial = serial.Serial(
            baudrate=self._baudrate,
            timeout=self._timeout,
        )  # create a closed serial connection
        self._con.port = str(self._port)

        if self._ps1 is None:
            self._ps1 = self.shell(
                command="", print_input=False, print_output=False
            ).strip()

    # FIXME remove this from the CommunicatioLayer
    def read_file(
        self,
        path: PathType,
    ) -> str:
        pass

    def use_shell(self) -> None:
        self._is_shell = True
        list_of_methods_to_use: list[str] = [
            "file_size",
            "path_exists",
        ]
        # HACK we dynamically add the methods of SSHCommLayer to this class, as
        # they are close to what it would be to implement them for UART
        for foo in list_of_methods_to_use:
            setattr(
                self,
                foo,
                types.MethodType(getattr(SSHCommLayer, foo), self),
            )

    def is_open(self) -> bool:
        return self._con.is_open  # type: ignore

    def start_comm(self) -> None:
        if self.is_open():
            raise RuntimeError("Communication layer is already open.")
        self._con.open()

    def close_comm(self) -> None:
        if not self.is_open():
            raise RuntimeError("Communication layer is not open.")
        self._unchecked_close_comm()

    def _unchecked_close_comm(self) -> None:
        self._con.close()  # type: ignore

    def listen(
            self,
            chunk_size: int = 16,
            timeout: float = 1.0,
            timeout_per_input: bool = False,
    ) -> str:
        """
        Listen to the UART for a given amount of time and return the output.
        Args:
            chunk_size (int, optional): number of bytes to read at a time. Defaults to 16.
            timeout (float, optional): number of seconds to listen for. Defaults to 1.
            timeout_per_input (bool, optional): whether to reset the timeout after each input is received. Defaults to False.
        Returns:
            str: the output received from the UART.
        """

        if not self.is_open():
            self.start_comm()

        buffer: list[bytes] = list()
        before: float  = time.time()

        while time.time() - before < timeout :
            if not self._con.readable():
                break

            buffer.append(self._con.read(chunk_size))
            before = time.time() if timeout_per_input else before


        self.close_comm()
        return b''.join(buffer).decode('utf-8').removesuffix("\n").removesuffix("\r")

    def shell(
        self,
        command: Command,
        std_input: str | None = None,
        current_dir: PathType | None = None,
        environment: Environment = None,
        shell: bool = False,
        print_input: bool = True,
        print_output: bool = True,
        print_curdir: bool = True,
        timeout: int | None = None,
        output_is_log: bool = False,
        ignore_ret_codes: Iterable[int] = (),
        ignore_any_error_code: bool = False,
    ) -> str:
        """Run a shell command on the target host.

        Args:
            command (Command):
                command to run on the target host.
            std_input (str | None, optional):
                input to pipe into the command to run, None if there is no input to provide.
                Defaults to None.
            current_dir (PathType | None, optional):
                directory where to run the command. Defaults to None.
            environment (Environment, optional):
                environment to pass to the command to run. Defaults to None.
            shell (bool, optional):
                whether a shell must be created to run the command. Defaults to False.
            print_input (bool, optional):
                whether to print the command on benchkit logs. Defaults to True.
            print_output (bool, optional):
                whether to print the command output on benchkit logs. Defaults to True.
            print_curdir (bool, optional):
                whether to print the current directoru on benchkit logs. Defaults to True.
            timeout (int | None, optional):
                number of seconds to wait for the command to complete, or None for no timeout.
                Defaults to None.
            output_is_log (bool, optional):
                whether the output of the command is expected to be logging (e.g., when running
                `cmake`). If it is the case, the logging will be printed in a `tail -f` fashion.
                Defaults to False.
            ignore_ret_codes (Iterable[int], optional):
                List of error code to ignore if it is the return code of the command.
                Defaults to () (empty collection).
            ignore_any_error_code (bool, optional):
                whether to error any error code returned by the command.

        Returns:
            str: the output of the command.
        """
        if not self.is_open():
            self.start_comm()

        cmd: str = " ".join(command) if isinstance(command, (list, tuple)) else command

        if print_input:
            print(f"[input]{cmd}")

        writtren_bytes: int = self._con.write(cmd.encode() + b"\n")  # type: ignore

        if writtren_bytes != len(cmd) + 1:
            raise RuntimeError("Failed to write the full command to UART.")
        # 7-bit C1 ANSI sequences
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        ret: str = ansi_escape.sub("", self._con.readall().decode())
        if self._ps1 is not None:
            ret = ret.replace(self._ps1, "")
        ret = ret.replace(cmd, "").strip()

        if print_output:
            print(ret)

        self.close_comm()  # do not hog the port when not in use
        return ret

    @property
    def remote_host(self) -> str | None:
        """Returns an identifier (typically hostname) of the remote host, or None if communication
        happens locally.

        Returns:
            str | None: name of the remote host or None if communication happens locally.
        """
        return None

    @property
    def is_local(self) -> bool:
        """Returns whether the communication layer happens locally on the host.

        Returns:
            bool: whether the communication layer happens locally on the host.
        """
        return False

    # FIXME this should be removed from the CommunicationLayer
    @property
    def ip_address(self) -> str:
        """Returns the IP address of the host.

        Returns:
            str: IP address of the host.
        """
        return ""
