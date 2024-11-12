# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Management of USB, especially for taking a USB port down and up.
"""

import os
import platform as sys_platform
import re
import time
from typing import List, Optional

from benchkit.shell.shell import shell_out
from benchkit.utils.types import PathType


class UsbDevice:
    """Represent a USB device."""

    def __init__(
        self,
        bus: str,
        dev: str,
        vendor_id: str,
        product_id: str,
        name: str,
    ) -> None:
        self.bus = bus
        self.dev = dev
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.name = name

    def linux_path(self) -> PathType:
        """Finds the path, on Linux, of the current USB device.

        Returns:
            PathType: the path of the current USB device.
        """

        def check_file_content(
            pathname: PathType,
            expected_content: str,
        ) -> bool:
            if not os.path.isfile(pathname):
                return False
            with open(pathname, "r") as file:
                actual_content = file.read().strip()
            return expected_content == actual_content

        devices_path = "/sys/bus/usb/devices"
        for device_file in os.listdir("/sys/bus/usb/devices"):
            device_path = os.path.join(devices_path, device_file)

            id_vendor_path = os.path.join(device_path, "idVendor")
            id_product_path = os.path.join(device_path, "idProduct")

            right_id_vendor = check_file_content(
                pathname=id_vendor_path,
                expected_content=self.vendor_id,
            )
            right_id_product = check_file_content(
                pathname=id_product_path,
                expected_content=self.product_id,
            )

            if right_id_vendor and right_id_product:
                return device_path

        raise ValueError(f"Cannot find path for usb device {self.vendor_id}:{self.product_id}")


def _lsusb() -> List[UsbDevice]:
    def usbdevice_from_line(line: str) -> UsbDevice:
        m = re.match(
            pattern=(
                r"Bus (?P<bus>\d+) Device (?P<dev>\d+): ID "
                r"(?P<vendor_id>[0-9a-zA-Z]{4}):"
                r"(?P<product_id>[0-9a-zA-Z]{4}) "
                r"(?P<name>.*)$"
            ),
            string=line,
        )
        if m is None:
            raise ValueError("Cannot parse usb device from lsusb line")
        gd = m.groupdict()

        return UsbDevice(**gd)

    output = shell_out(
        command="lsusb",
        print_input=False,
        print_output=False,
    ).strip()
    devices = [usbdevice_from_line(line=line.strip()) for line in output.splitlines()]
    return devices


def _find_phone_usb_dev() -> Optional[UsbDevice]:
    devices = [dev for dev in _lsusb() if "RNDIS" in dev.name]
    if len(devices) > 1:
        raise ValueError("Several RNDIS devices connected. Not supported.")
    if len(devices) == 1:
        return devices[0]
    return None


def usb_down_up() -> None:
    """Find the USB device for the connected target phone
    and bring the corresponding USB port down and up again.
    """
    if "Linux" != sys_platform.system():
        return

    phone_dev = _find_phone_usb_dev()
    if phone_dev is None:
        return

    device_path = phone_dev.linux_path()
    auth_path = os.path.join(device_path, "authorized")
    shell_out(
        command=f"sudo tee {auth_path}",
        std_input="0",
        print_input=False,
        print_output=False,
    )
    time.sleep(1)
    shell_out(
        command=f"sudo tee {auth_path}",
        std_input="1",
        print_input=False,
        print_output=False,
    )
    time.sleep(3)
