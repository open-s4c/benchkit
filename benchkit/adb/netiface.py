# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Configuration of the network interface for the phone through RNDIS driver.
"""

import platform as sys_platform
import sys
import time
from typing import List

from benchkit.adb import AndroidDebugBridge
from benchkit.adb.fastboot import Fastboot, FastbootError
from benchkit.utils.netplan import Netplan, get_iface_current_ip, get_list_iface_names

_IFACE_PREFIX = "enx"


class NetifaceError(Exception):
    """For errors related to this module."""


class NetifaceNoIfaceError(NetifaceError):
    """Error for case when not network interface are found."""


class NetifaceSeveralIfacesError(NetifaceError):
    """Error when there are several network interface candidates."""


def _get_iface_candidates() -> List[str]:
    iface_candidates = [
        iface for iface in get_list_iface_names() if iface.startswith(_IFACE_PREFIX)
    ]
    return iface_candidates


def check_phone_netiface(host_ip: str) -> None:
    """Check whether the phone interface is configured correctly for the target phone.

    Args:
        host_ip (str): IP address of the host.

    Raises:
        NetifaceNoIfaceError: if no interface is found to match the phone.
        NetifaceSeveralIfacesError: if several interfaces are found to match the phone.
    """
    iface_candidates = _get_iface_candidates()

    match len(iface_candidates):
        case 0:
            print(
                (
                    "[WARNING] Impossible to find phone network interface. "
                    "The phone is probably disconnected from host "
                    "(or in fastboot state)."
                ),
                file=sys.stderr,
            )
            return
        case 1:
            nb_trials = 1
            max_nb_trials = 8
            wait_time = 1
            done = False
            while nb_trials <= max_nb_trials:
                iface_name = "N/A"
                iface_candidates = _get_iface_candidates()
                if iface_candidates:
                    iface_name = iface_candidates[0]
                    iface_ip = get_iface_current_ip(iface_name=iface_name)
                    if host_ip == iface_ip:
                        done = True
                if done:
                    break
                print(
                    (
                        f"[INFO] check_phone_netiface: ({nb_trials}/{max_nb_trials}) waiting "
                        f'for phone netiface "{iface_name}" '
                        f'to get its host static ip "{host_ip}"'
                    )
                )
                time.sleep(wait_time)
                wait_time *= 2
                nb_trials += 1

            found = False
            iface_candidates = _get_iface_candidates()
            if iface_candidates:
                iface_name = iface_candidates[0]
                iface_ip = get_iface_current_ip(iface_name=iface_name)
                if host_ip == iface_ip:
                    found = True
            if not found:
                raise NetifaceNoIfaceError(
                    "Impossible to set target network interface after netplan configuration."
                )
        case _:
            raise NetifaceSeveralIfacesError(
                (
                    f"Several network interfaces have "
                    f'"{_IFACE_PREFIX}*" prefix. '
                    f"Sort that out before proceeding."
                )
            )


def configure_generic_phone_netiface(
    host_ip: str,
    target_ip: str,
    set_fastboot: bool,
    set_adb: bool,
) -> None:
    """Configure the network interface for the target phone and possible set up fastboot or adb.

    Args:
        host_ip (str): IP address of the host.
        target_ip (str): IP address of the target phone (on the RNDIS interface).
        set_fastboot (bool): whether to enable fastboot after the configuration is performed.
        set_adb (bool): whether to enable adb after the configuration is performed.

    Raises:
        ValueError: if both set_fastboot and set_adb are set. Only one can be choose at a time.
        FastbootError: if fastboot cannot find target device after triggering the reboot.
    """
    if "Linux" == sys_platform.system():
        pattern_iface_name = "phone"

        current_static_ip_addresses = Netplan.get_static_ip(iface_name=pattern_iface_name)
        if not current_static_ip_addresses or f"{host_ip}/24" != current_static_ip_addresses[0]:
            with Netplan() as netplan:
                netplan.set_static_ip_for_pattern(
                    pattern=f"{_IFACE_PREFIX}*",
                    ip=host_ip,
                )

    if set_fastboot and set_adb:
        raise ValueError("Impossible to set both fastboot and adb. Choose one.")
    if set_fastboot:
        with Fastboot(target_ip=target_ip) as fastboot:
            tries = 3
            while tries > 0:
                devices = list(fastboot.devices())
                if devices:
                    break
                tries -= 1
                time.sleep(2)
            if not devices:
                raise FastbootError("No device found with fastboot after booting.")
    if set_adb:
        with AndroidDebugBridge(ip_addr=target_ip) as adb:
            adb.wait_for("device")
