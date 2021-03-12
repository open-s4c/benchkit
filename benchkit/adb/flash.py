# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Single primitive to flash a boot image on a target phone through the RNDIS driver.
"""

import time

from benchkit.adb import AndroidDebugBridge
from benchkit.adb.fastboot import Fastboot
from benchkit.adb.netiface import (
    NetifaceNoIfaceError,
    check_phone_netiface,
    configure_generic_phone_netiface,
)
from benchkit.adb.usb import usb_down_up
from benchkit.utils.misc import TimeMeasure
from benchkit.utils.netplan import ping
from benchkit.utils.types import PathType


def flash_boot_image(
    boot_image_path: PathType,
    host_ip: str,
    target_ip: str,
    post_flash_wait_seconds: int,
) -> float:
    """Flash the give boot image on the target phone through the RNDIS driver.

    Args:
        boot_image_path (PathType): path on the host where the boot image file is located.
        host_ip (str): IP address of the host.
        target_ip (str): IP address of the target phone (according to RNDIS driver configuration).
        post_flash_wait_seconds (int): number of seconds to wait (for booting) after flashing.

    Returns:
        float: the duration in seconds of the total boot time.
    """
    with Fastboot(target_ip=target_ip) as fastboot:
        fastboot.flash_boot(boot_img_path=boot_image_path)

    with TimeMeasure() as boot_time:
        with Fastboot(target_ip=target_ip) as fastboot:
            fastboot.reboot()

        print(
            f"[INFO] Boot image flashed on phone. "
            f"Now sleeping a bit ({post_flash_wait_seconds}s) "
            f"to let the phone the time to boot..."
        )
        start_countdown = 60
        if post_flash_wait_seconds <= start_countdown:
            time.sleep(post_flash_wait_seconds)
        else:
            time.sleep(post_flash_wait_seconds - start_countdown)
            remaining_time = start_countdown
            while remaining_time > 0:
                print(f"[INFO] Remaining sleep time: {remaining_time} seconds...")
                time.sleep(10)
                remaining_time -= 10

        wait_time = 2
        while not ping(ip_address=target_ip):
            print(f"[INFO] pinging phone failed. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            wait_time *= 2
            try:
                check_phone_netiface(host_ip=host_ip)
            except NetifaceNoIfaceError:
                configure_generic_phone_netiface(
                    host_ip=host_ip,
                    target_ip=target_ip,
                    set_fastboot=False,
                    set_adb=False,
                )
            usb_down_up()
            print("[INFO] pinging phone...")
        print("[INFO] pinging phone succeeded.")

        with AndroidDebugBridge(ip_addr=target_ip) as adb:
            adb.wait_complete_boot()

    # TODO not yet perfect, since there is the sudo & the exponential backoff
    return boot_time.duration_seconds
