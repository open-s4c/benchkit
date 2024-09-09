# SPDX-License-Identifier: MIT
"""
Module to handle hdc (harmony debug bridge) interactions between host and remote phone.
"""
from typing import Iterable, Optional

from benchkit.shell.shell import get_args, shell_out
from benchkit.utils.types import Command, PathType


def _identifier_from(ip_addr: str, port: int) -> str:
    return f"{ip_addr}:{port}"


class HDCError(Exception):
    """Handle for errors from adb."""


class HDCDevice:
    """Representation of a device connected through hdc."""

    def __init__(
        self,
        ip_addr: str,
        port: str,
    ) -> None:
        self.ip_addr = ip_addr
        self.port = port

    def __str__(self) -> str:
        return f"{self.ip_addr}:{self.port}"
    

class HarmonyDebugBridge:
    """Operations with the phone for high-level hdc operations."""

    def __init__(
        self,
        ip_addr: str,
        port: int = 5555,
        keep_connected: bool = False,
        wait_connected: bool = False,
        expected_os: Optional[str] = None,
    ) -> None:
        self._ip = ip_addr
        self._port = port
        self._keep_connected = keep_connected
        self._wait_connected = wait_connected
        self._expected_os = expected_os


    def __init__(
        self, 
        device: HDCDevice,
        keep_connected: bool = False,
        wait_connected: bool = False,
        expected_os: Optional[str] = None,
    ) -> None:
        self._ip = device.ip_addr
        self._port = device.port
        self._keep_connected = keep_connected
        self._wait_connected = wait_connected
        self._expected_os = expected_os


    @property
    def identifier(self) -> str:
        """Get hdc identifier of current device.

        Returns:
            str: hdc identifier of current device.
        """
        return _identifier_from(ip_addr=self._ip, port=self._port)


    def _find_device(self) -> Optional[HDCDevice]:
        devices = [dev for dev in self._devices() if dev.identifier == self.identifier]
        match len(devices):
            case 0:
                return None
            case 1: 
                return devices[0]
            case _:
                raise ValueError("Wrong device list.")
            

    @staticmethod
    def _devices() -> Iterable[str]:
        """Get list of devices recognized by hdc.

        Raises:
            HDCError: if hdc is not working as expected.

        Returns:
            Iterable[HDCDevice]: list of devices recognized by hdc.
        """
        output = HarmonyDebugBridge._host_shell_out(command="hdc list targets")
        device_ids = output.strip().splitlines()
        devices = []
        for dev in device_ids:
            device = dev.split(":")
            if len(device) != 2:
                raise HDCError("Could not parse hdc output")
            devices.append(HDCDevice(device[0], device[1]))
        
        return devices


    @staticmethod
    def _host_shell_out(
        command: Command,
        timeout: Optional[int] = None,
        print_input: bool = False,
        print_output: bool = False,
    ) -> str:
        output = shell_out(
            command=command,
            timeout=timeout,
            print_input=print_input,
            print_output=print_output,
        )
        return output
    
    
    def _target_shell_out(
        self,
        command: Command,
        current_dir: Optional[PathType] = None,
        output_is_log: bool = False,
    ) -> str:
        dir_args = ["cd", f"{current_dir}", "&&"] if current_dir is not None else []
        command_args = dir_args + get_args(command)

        hdc_command = [
            "hdc",
            "-t",
            f"{self.identifier}",
            "shell"
        ] + command_args

        output = shell_out(
            command=hdc_command,
            print_output=False,
            output_is_log=output_is_log,
        )

        return output


    def shell_out(
        self,
        command: Command,
        current_dir: Optional[PathType] = None,
        output_is_log: bool = False,
    ) -> str:
        """Executes a shell command through hdc.

        Args:
            command (Command): command to execute
            current_dir (Optional[PathType], optional): directory where to execute the command.
                                                        Defaults to None.
            output_is_log (bool, optional): whether the expected output is logging (will then be
                                            displayed accordingly). Defaults to False.

        Returns:
            str: _description_
        """
        return self._target_shell_out(
            command=command,
            current_dir=current_dir,
            output_is_log=output_is_log,
        )
    

    def push(
        self,
        local_path: PathType,
        remote_path: PathType,
    ) -> None:
        """Push a file from the local host to the device through hdc.
        Internally using the `hdc file send` command

        Args:
            local_path (PathType): path on the host where the file is.
            remote_path (PathType): path where to push the file on the device.
        """
        command = [
            "hdc",
            "-t",
            f"{self.identifier}",
            "file",
            "send",
            f"{local_path}",
            f"{remote_path}"
        ]
        self._host_shell_out(command=command)

    def pull(
        self,
        remote_path: PathType,
        local_path: PathType,
    ) -> None:
        """Pull a file from the device to the local host through hdc.
        Internally using the `hdc file recv` command

        Args:
            remote_path (PathType): path on the device where the file is.
            local_path (PathType): path where to pull the file on the host.
        """
        commmand = [
            "hdc",
            "-t",
            f"{self.identifier}",
            "file",
            "recv",
            f"{remote_path}",
            f"{local_path}"
        ]
        self._host_shell_out(command=commmand)
