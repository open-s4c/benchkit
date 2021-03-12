# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to handle adb (android debug bridge) interactions between host and remote phone.
"""

import socket
import subprocess
import sys
import time
from typing import Iterable, Optional

from benchkit.adb.usb import usb_down_up
from benchkit.shell.shell import get_args, shell_out
from benchkit.utils.types import Command, PathType


def _identifier_from(ip_addr: str, port: int) -> str:
    return f"{ip_addr}:{port}"


class ADBError(Exception):
    """Handle for errors from adb."""


class ADBDevice:
    """Representation of a device connected through adb."""

    def __init__(
        self,
        identifier: str,
        status: str,
    ) -> None:
        self.identifier = identifier
        self.status = status

    def is_connected(self) -> bool:
        """Check if the current device is connected.

        Returns:
            bool: whether the currrent device is connected.
        """
        return "device" == self.status


class AndroidDebugBridge:  # TODO add commlayer for "host"
    """Operations with the phone for high-level adb operations."""

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

    def __enter__(self) -> "AndroidDebugBridge":
        if not self.is_connected():
            self._connect_daemon()
            if self._wait_connected:
                self.wait_complete_boot()
                if self._expected_os is not None:
                    self.check_connection(expected_os=self._expected_os)

        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        if not self._keep_connected and self.is_connected():
            self._disconnect()

    @property
    def identifier(self) -> str:
        """Get adb identifier of current device.

        Returns:
            str: adb identifier of current device.
        """
        return _identifier_from(ip_addr=self._ip, port=self._port)

    def is_connected(self) -> bool:
        """Returns whether the device is connected to adb.

        Returns:
            bool: whether the device is connected to adb.
        """
        device = self._find_device()
        result = device is not None and device.is_connected()
        return result

    def check_connection(
        self,
        expected_os: str,
    ) -> None:
        """Check the connection is established between current device and adb and ensure the
        current os is the expected one.

        Args:
            expected_os (str): expected operating system to be currently running on device.

        Raises:
            ADBError: if device is not recognized by adb (not in "device" state).
            ADBError: if device is not running the expected operating system.
        """
        device = self._find_device()

        if "device" != device.status:
            raise ADBError('Connection check: device not in "device" state. Aborting.')

        output = self.shell_out(command="uname -a")
        actual_os, _, _, _, _ = output.strip().split()

        if expected_os != actual_os:
            raise ADBError(
                f'Connection check: expected OS is "{expected_os}", '
                'whereas actual OS is "{actual_os}"'
            )

    def _find_device(self) -> Optional[ADBDevice]:
        devices = [d for d in self._devices() if d.identifier == self.identifier]

        match len(devices):
            case 0:
                return None
            case 1:
                return devices[0]
            case _:
                raise ValueError("Wrong device list.")

    def _connect_daemon(self) -> None:
        # first attempt a socket connection to see if the port is open
        # if the phone is booting, "adb connect" command will stall
        wait_time = 1
        connected = False
        while wait_time < 60:
            with socket.socket(socket.AF_INET) as conn_sock:
                conn_sock.settimeout(wait_time)
                try:
                    conn_sock.connect((self._ip, self._port))
                    connected = True
                except TimeoutError:
                    wait_time *= 2
                except ConnectionRefusedError:
                    wait_time *= 2
                except OSError as err:
                    if 113 == err.errno:  # "no route to host"
                        assert "No route to host" == err.strerror
                    else:
                        raise err
                if connected:
                    break
                usb_down_up()

        try:
            self._connect(timeout=30)
            time.sleep(1)
            self.wait_for()
        except subprocess.TimeoutExpired:
            raise ADBError("Connection timeout")

        if not self.is_connected():
            raise ADBError("Problem with adb connection")

    def _connect(self, timeout: int) -> None:
        ip_port = f"{self._ip}:{self._port}"
        succeed = False
        wait_time = 1
        while not succeed:
            output = self._host_shell_out(
                command=f"adb connect {ip_port}",
                timeout=timeout,
            )
            connection_output = output.strip()

            output_connected = f"connected to {ip_port}"
            output_already_connected = f"already connected to {ip_port}"
            output_failed_to_connect = f"failed to connect to {ip_port}"
            output_connection_refused = f"failed to connect to '{ip_port}': Connection refused"

            if connection_output in [output_connected, output_already_connected]:
                succeed = True
            elif connection_output in [output_failed_to_connect, output_connection_refused]:
                wait_time *= 2
                print(
                    (
                        f"[WARNING] Connection refused to adb, "
                        f"trying again in {wait_time} seconds..."
                    ),
                    file=sys.stderr,
                )
                time.sleep(wait_time)
            else:
                raise ADBError(f'Unknown "adb connect" output: {connection_output}')

    def _disconnect(self) -> None:
        self._host_shell_out(command=f"adb disconnect {self._ip}:{self._port}")

    @staticmethod
    def _devices() -> Iterable[ADBDevice]:
        """Get list of devices recognized by adb.

        Raises:
            ADBError: if adb is not working as expected.

        Returns:
            Iterable[ADBDevice]: list of devices recognized by adb.
        """
        output = AndroidDebugBridge._host_shell_out(command="adb devices")
        header, *device_lines = output.strip().splitlines()

        if "List of devices attached" != header:
            raise ADBError("Could not parse adb output")

        devices = [ADBDevice(*line.split("\t")) for line in device_lines]

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

        adb_command = [
            "adb",
            "-s",
            f"{self.identifier}",
            "shell",
        ] + command_args

        output = shell_out(
            command=adb_command,
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
        """Executes a shell command through adb.

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
        """Push a file from the local host to the device through adb.

        Args:
            local_path (PathType): path on the host where the file is.
            remote_path (PathType): path where to push the file on the device.
        """
        command = [
            "adb",
            "push",
            f"{local_path}",
            f"{remote_path}",
        ]
        self._host_shell_out(command=command)

    def pull(
        self,
        remote_path: PathType,
        local_path: PathType,
    ) -> None:
        """Pull a file from the device to the local host through adb.

        Args:
            remote_path (PathType): path on the device where the file is.
            local_path (PathType): path where to pull the file on the host.
        """
        command = [
            "adb",
            "pull",
            f"{remote_path}",
            f"{local_path}",
        ]
        self._host_shell_out(command=command)

    def wait_for(
        self,
        state: str = "device",
        transport: Optional[str] = None,
    ):
        """Wait for device to be in the given state. See `man adb` for details.

        Args:
            state (str, optional): expected state after wait. Defaults to "device".
            transport (Optional[str], optional): protocol used. Defaults to None.
        """
        transport_str = f"-{transport}" if transport is not None else ""
        command = ["adb", f"wait-for{transport_str}-{state}"]
        self._host_shell_out(
            command=command,
            print_input=True,
            print_output=True,
        )

    def reboot_fastboot(self) -> None:
        """Use adb to reboot the device in fastboot mode (bootloader)."""
        self._host_shell_out(command="adb shell reboot bootloader")

    def has_completely_booted(self) -> bool:
        """Return whether the device has finished booting.

        Returns:
            bool: Whether the device has finished booting.
        """
        launcher_output = self._target_shell_out("ps | grep launcher")
        result1 = "com.huawei.android.launcher" in launcher_output

        boot_prop = self._get_prop(prop_name="sys.boot_completed")
        result2 = "1" == boot_prop

        result = result1 and result2
        return result

    def wait_complete_boot(self) -> None:
        """Wait for the device to complete boot phase with an incremental timeout."""
        wait_time = 1
        while not self.has_completely_booted():
            wait_time += 1
            print(
                "[INFO] Phone has not completely booted the Android framework yet. "
                f"Waiting {wait_time} seconds..."
            )
            time.sleep(wait_time)

    def unlock_phone(self) -> None:
        """Send touch command through adb to unlock the phone."""
        self._target_shell_out("input keyevent KEYCODE_WAKEUP")
        time.sleep(1)
        self._target_shell_out("input swipe 500 2000 500 200")

    def clear_all_apps(self) -> None:
        """Ends all applications running on the phone."""
        self.push_button_home()
        self.push_button_home()
        self.push_button_switch()
        self.screen_tap(x=560, y=2180)

    def screen_tap(
        self,
        x: int,
        y: int,
    ) -> None:
        """Tap on the remote phone through adb at the given coordinates.

        Args:
            x (int): x-coordinate of the pixel to tap.
            y (int): y-coordinate of the pixel to tap.
        """
        self._target_shell_out(command=f"input tap {x} {y}")

    def _input_key(
        self,
        keycode: str,
    ) -> None:
        """Input a certain key through adb.

        Args:
            keycode (str): the key to input.
        """
        self._target_shell_out(f"input keyevent {keycode}")

    def _get_prop(self, prop_name: str) -> str:
        """Get a property of the running system on the remote device.

        Args:
            prop_name (str): the property name.

        Returns:
            str: the value of the given property.
        """
        output = self._target_shell_out(command=f"getprop {prop_name}")
        result = output.strip()
        return result

    def push_button_home(self) -> None:
        """Input the "HOME" key on the remote phone (circle symbol)."""
        self._input_key(keycode="KEYCODE_HOME")

    def push_button_switch(self) -> None:
        """Input the "SWITCH" key on the remote phone (square symbol)."""
        self._input_key(keycode="KEYCODE_APP_SWITCH")

    def is_installed(self, activity_name: str) -> bool:
        """Return whether the given activity is installed on the system of the remote device.

        Args:
            activity_name (str): name of the given activity.

        Returns:
            bool: Whether the given activity is installed on the system of the remote device.
        """
        command = f"pm list packages -e {activity_name}"
        output = self._target_shell_out(command)
        is_installed = f"package:{activity_name}" == output.strip()
        return is_installed
