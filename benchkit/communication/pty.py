# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Communication layer to handle a PTY device.

A PTY device is a file that behaves like a terminal. It is mostly used to
communicate with embedded devices over a serial connection (e.g., /dev/ttyUSB0
on Linux). Or, an virtual terminal on the local machine.

As this module interacts with low-level OS features, it is only supported on
Unix-like on a local host.
"""

import os
import select
from typing import List

from benchkit.communication import CommunicationLayer
from benchkit.utils.types import Command, PathType

CHUNK_SIZE: int = 1024


class StatusAware:
    """
    Abstract class for communication layers that are aware of their connection status.
    NOTE: use a python interface ?
    """

    """
    Returns whether the communication layer is open.
    """

    def is_open(self) -> bool: ...

    """
    Starts the communication layer.
    """

    def start_comm(self) -> None: ...

    """
    Performs checks then, closes the communication layer.
    """

    def close_comm(self) -> None: ...

    """
    Closes the communication layer without checking whether it is open.
    """

    def _unchecked_close_comm(self) -> None: ...


class PTYException(Exception):
    pass


class PtyCommLayer(CommunicationLayer, StatusAware):
    """
    Communication layer to handle a PTY device.
    """

    def __init__(
        self,
        port: PathType,
    ) -> None:
        """
        Initializes the PTY communication layer.
        Args:
            port (PathType):
                path to the PTY device.
        """

        self._port: PathType = port
        self._fd: int | None = None
        self._ps1: str = ""  # only for shells : make it optional ?

        super().__init__()

    def __enter__(self):
        """
        Context manager entry point for the PTY communication layer.
        """

        if self.is_open():
            raise PTYException("The comm layer is already running")
        self.start_comm()
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """
        Context manager exit point for the PTY communication layer.
        """
        self._unchecked_close_comm()  # when using the context manager, the comm
        # should always be opened at __exit__
        return False

    @property
    def remote_host(self) -> str | None:
        """
        Returns an identifier (typically hostname) of the remote host, or None if communication
        happens locally.

        Returns:
            str | None: name of the remote host or None if communication happens locally.
        """
        return None

    @property
    def is_local(self) -> bool:
        """
        Returns whether the communication layer happens locally on the host.

        Returns:
            bool: whether the communication layer happens locally on the host.
        """
        return False

    def pipe_shell(
        self,
        command: Command,
        current_dir: Optional[PathType] = None,
        shell: bool = False,
        print_command: bool = True,
        ignore_ret_codes: Iterable[int] = (),
    ):
        return NotImplemented

    def shell(
        self,
        command: Command,
        std_input: str | None = None,
        current_dir: PathType | None = None,
        environment: Environment = None,
        shell: bool = False,
        print_input: bool = True,
        print_output: bool = True,
        print_curdir: bool = False,
        timeout: int = 1,
        output_is_log: bool = False,
        ignore_ret_codes: Iterable[int] = (),
        ignore_any_error_code: bool = False,
    ) -> str:
        """
        Run a shell command on the target host.

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
            timeout (int):
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
        if (
            current_dir is not None
            or shell
            or print_curdir
            or output_is_log
            or ignore_any_error_code
            or ignore_ret_codes != ()
        ):
            raise PTYException("Unsupported attributes")
        elif not self.is_open():
            raise PTYException("The port is closed : open a communication before sending a command")

        command_str: str = ""
        if environment is not None:
            environment: List[str] = [f"{k}={v}" for k, v in dict(environment).items()]
            command_str += " ".join(environment)

        if isinstance(command, list):
            command_str += " ".join(command)
        elif isinstance(command, str):
            command_str += command
        else:
            raise PTYException("Not a valid command type")

        if std_input is not None:
            command_str += f"| {std_input}"

        if not command_str.endswith("\n"):
            command_str += "\n"

        os.write(self._fd, command_str.encode())
        output: str = self.listen().decode(errors="replace")
        output = output.replace(command_str.replace("\n", ""), "").replace(self._ps1, "").strip()

        if print_input:
            print(command_str.replace("\n", ""))

        if print_output:
            print(output)

        return output

    def is_open(self) -> bool:
        return self._fd is not None

    def start_comm(self) -> None:
        self._fd = os.open(self._port, os.O_RDWR | os.O_NOCTTY)
        _: bytearray = self.listen(timeout=0.5)  # consuming the boot log if any
        self._ps1 = self.shell(command="", print_input=False, print_output=False)  # calibration

    def listen(self, timeout: float = 1.0) -> bytearray:
        if not self.is_open():
            raise PTYException("The port is not open : cannot listen")

        buf: bytearray = bytearray()
        while True:
            r, _, _ = select.select([self._fd], [], [], float(timeout))
            if not r:
                break
            chunk: bytes = os.read(self._fd, CHUNK_SIZE)
            buf.extend(chunk)

        return buf

    def close_comm(self) -> None:
        """
        Closes the PTY communication layer after performing checks.
        """
        if self.is_open():
            os.close(self._fd)
        else:
            raise PTYException("The comm layer was manually closed or something else smh")

    def _unchecked_close_comm(self) -> None:
        """
        Closes the PTY communication layer without performing checks.
        """
        os.close(self._fd)
