# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interact with a remote phone using fastboot primitives (flashing, rebooting, etc.).
It assumes the phone is in fastboot mode.
"""

import os.path
import sys
import time
from typing import Iterable

from benchkit.adb import AndroidDebugBridge
from benchkit.shell.shell import shell_out
from benchkit.utils.types import PathType


class FastbootError(Exception):
    """Handle for errors from fastboot."""


class Fastboot:  # TODO add commlayer for "host"
    """Operations with the phone for low-level fastboot operations."""

    def __init__(
        self,
        target_ip: str,
    ) -> None:
        self._device = None
        self._target_ip = target_ip

    def __enter__(self) -> "Fastboot":
        devices = self.devices()

        if not devices:
            with AndroidDebugBridge(ip_addr=self._target_ip) as adb:
                adb.reboot_fastboot()

            wait_time = 1
            while not devices and wait_time < 60:
                wait_time *= 2
                time.sleep(wait_time)
                devices = self.devices()

        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        pass

    @staticmethod
    def devices() -> Iterable[str]:
        """Get list of devices

        Returns:
            Iterable[str]: list of device identifiers
        """

        def fastboot_devices() -> str:
            return shell_out(command="fastboot devices")

        output = fastboot_devices()
        if not output:  # we try a second time
            time.sleep(2)
            output = fastboot_devices()

        device_lst = [d.split("\t")[0] for d in output.strip().splitlines()]
        return device_lst

    @staticmethod
    def reboot() -> None:
        """Trigger a reboot of the remote phone"""
        shell_out(
            command="fastboot reboot",
            output_is_log=True,
        )
        sys.stdout.flush()
        sys.stderr.flush()

    @staticmethod
    def flash(
        partition: str,
        file_path: PathType,
    ) -> None:
        """Flash given partition with file

        Args:
            partition (str): partition name to flash
            file_path (PathType): path of the file to flash on partition
        """
        filedir, filename = os.path.split(file_path)
        shell_out(
            command=f"fastboot flash {partition} ./{filename}",
            current_dir=filedir,
            print_input=True,
            print_output=True,
            output_is_log=True,
        )

    def flash_boot(
        self,
        boot_img_path: PathType,
    ) -> None:
        """Flash boot partition with given file

        Args:
            boot_img_path (PathType): Path of the image to flash on device
        """
        self.flash(
            partition="boot",
            file_path=boot_img_path,
        )
