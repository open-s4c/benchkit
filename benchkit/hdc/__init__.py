# SPDX-License-Identifier: MIT
"""
Module to handle hdc (OpenHarmony Device Connector) interactions between host and remote phone.
HDC documentation: https://docs.openharmony.cn/pages/v5.0/en/application-dev/dfx/hdc.md 
"""
from enum import Enum
from platform import system as os_system
from typing import Callable, Iterable, List, Optional

from benchkit.dependencies.executables import ExecutableDependency
from benchkit.dependencies.packages import Dependency
from benchkit.shell.shell import get_args, shell_out
from benchkit.utils.types import Command, PathType


class HDCError(Exception):
    """Handle for errors from hdc."""


class DeviceIdentifierKind(Enum):
    IP_AND_PORT = 0
    SERIAL = 1
    DONT_CARE = 2


class HDCDevice:
    """Representation of a device connected through hdc."""

    def __init__(
        self,
        identifier: str,
        kind: DeviceIdentifierKind = DeviceIdentifierKind.DONT_CARE,
    ) -> None:
        self.identifier = identifier
        self.kind = kind

    def __str__(self) -> str:
        return f"{self.identifier}"


class OpenHarmonyDeviceConnector:
    """Operations with the phone for high-level hdc operations."""

    def __init__(
        self,
        identifier: str,
        kind: DeviceIdentifierKind = DeviceIdentifierKind.DONT_CARE,
        keep_connected: bool = False,
        wait_connected: bool = False,
        expected_os: Optional[str] = None,
    ) -> None:
        self.identifier = identifier
        self.kind = kind
        self._keep_connected = keep_connected
        self._wait_connected = wait_connected
        self._expected_os = expected_os
        self._bin = "hdc.exe" if "Windows" == os_system() else "hdc"

    @staticmethod
    def from_device(
        device: HDCDevice,
        keep_connected: bool = False,
        wait_connected: bool = False,
        expected_os: Optional[str] = None,
    ) -> "OpenHarmonyDeviceConnector":
        return OpenHarmonyDeviceConnector(
            identifier=device.identifier,
            kind=device.kind,
            keep_connected=keep_connected,
            wait_connected=wait_connected,
            expected_os=expected_os,
        )

    def dependencies(self) -> List[Dependency]:
        return [ExecutableDependency(self._bin)]

    def _find_device(self) -> Optional[HDCDevice]:
        devices = [dev for dev in self._devices() if dev.identifier == self.identifier]
        match len(devices):
            case 0:
                return None
            case 1:
                return devices[0]
            case _:
                raise ValueError("Wrong device list.")

    def _devices(self) -> List[HDCDevice]:
        """Get list of devices recognized by hdc.

        Returns:
            Iterable[HDCDevice]: list of devices recognized by hdc.
        """
        output = OpenHarmonyDeviceConnector._host_shell_out(command=f"{self._bin} list targets")
        device_ids = output.strip().splitlines()
        devices = []
        for dev in device_ids:
            if ":" in dev:
                devices.append(HDCDevice(dev, DeviceIdentifierKind.IP_AND_PORT))
            else:
                devices.append(HDCDevice(dev, DeviceIdentifierKind.SERIAL))

        return devices

    def query_devices(
        self,
        filter_callback: Callable[[HDCDevice], bool] = lambda _: True,
    ) -> Iterable[HDCDevice]:
        """Get filtered list of devices recognized by hdc.

        Returns:
            Iterable[HDCDevice]: filtered list of devices recognized by hdc.
        """
        devices = self._devices()
        filtered = [dev for dev in devices if filter_callback(dev)]
        return filtered

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

        hdc_command = [f"{self._bin}", "-t", f"{self.identifier}", "shell"] + command_args

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
            "hdc.exe",
            "-t",
            f"{self.identifier}",
            "file",
            "send",
            f"{local_path}",
            f"{remote_path}",
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
        command = [
            f"{self._bin}",
            "-t",
            f"{self.identifier}",
            "file",
            "recv",
            f"{remote_path}",
            f"{local_path}",
        ]
        self._host_shell_out(command=command)
