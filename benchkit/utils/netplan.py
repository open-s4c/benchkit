# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interact with netplan to manage the network of the target.
"""

import platform as sys_platform
import re
import subprocess
import time
from typing import List, Optional

import netifaces

from benchkit.shell.shell import shell_out


class Netplan:  # TODO add commlayer for "host"
    """
    Interact with netplan.
    """

    def __init__(self):
        pass

    def __enter__(self):
        self._clear_manual_config()

        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        shell_out("sudo netplan apply")
        time.sleep(5)

    def set_static_ip_for_pattern(
        self,
        pattern: str,
        ip: str,
    ) -> None:
        """
        Set the given static IP address for the given pattern of netiface names.

        Args:
            pattern (str): pattern to match to the names of network interface.
            ip (str): ip address to set.
        """
        self._set_param(f"ethernets.phone.match.name={pattern}")
        self._set_param("ethernets.phone.dhcp4=false")
        self._set_param("ethernets.phone.dhcp6=false")
        self._set_param(f"ethernets.phone.addresses=[{ip}/24]")

    def set_static_ip(
        self,
        iface_name: str,
        ip: str,
    ) -> None:
        """
        Set static IP address to the given network interface.

        Args:
            iface_name (str): name of the network interface to which set the static IP address.
            ip (str): static IP address to set.
        """
        self._set_param(f"ethernets.{iface_name}.dhcp4=false")
        self._set_param(f"ethernets.{iface_name}.dhcp6=false")
        self._set_param(f"ethernets.{iface_name}.addresses=[{ip}/24]")

    @classmethod
    def get_static_ip(
        cls,
        iface_name: str,
    ) -> Optional[List[str]]:
        """
        Return the static IP address of the given network interface.

        Args:
            iface_name (str): name of the interface to get the IP address from.

        Raises:
            ValueError: if it is not possible to parse the IP address.

        Returns:
            Optional[List[str]]: list of IP addresses corresponding to the given network interface.
        """
        addresses_str = cls._get_param(f"ethernets.{iface_name}.addresses")

        if not addresses_str or "null" == addresses_str:
            return None

        def get_address(address_line: str) -> str:
            m = re.match(pattern=r'- "(?P<address>.*)"', string=address_line)
            if m is None:
                raise ValueError(
                    f'Impossible to parse address/mask from address line: "{address_line}"'
                )
            gd = m.groupdict()
            result = gd["address"]
            return result

        addresses = [
            get_address(address_line=address_line) for address_line in addresses_str.splitlines()
        ]

        return addresses

    @staticmethod
    def _get_param(param: str) -> str:
        result = shell_out(
            f"netplan get {param}",
            ignore_ret_codes=(1,),
        )
        return result.strip()

    @staticmethod
    def _set_param(param: str) -> None:
        shell_out(f"sudo netplan set {param}")
        shell_out("sudo chmod 644 /etc/netplan/70-netplan-set.yaml")

    @staticmethod
    def _clear_manual_config() -> None:
        shell_out("sudo rm -f /etc/netplan/70-netplan-set.yaml")


def get_list_iface_names() -> List[str]:
    """
    Get list of names of network interfaces.

    Returns:
        List[str]: list of names of network interfaces.
    """
    result = netifaces.interfaces()
    return list(result)


def get_iface_current_ip(iface_name: str) -> Optional[str]:
    """
    Get the current IP address of the given network interface (if it has one).

    Args:
        iface_name (str): name of the network interface to query.

    Returns:
        Optional[str]: the current IP address of the given network interface or None if has none.
    """
    if_info = netifaces.ifaddresses(iface_name)
    if netifaces.AF_INET not in if_info:
        return None
    address_info = if_info[netifaces.AF_INET]
    address = address_info[0]["addr"]
    return address


def ping(ip_address: str) -> bool:
    """
    Ping the given IPv4 address.

    Args:
        ip_address (str): IPv4 address to ping.

    Raises:
        ValueError: if the current operating system is neither Windows nor Linux.

    Returns:
        bool: whether the ping succeeded.
    """
    timeout = 1
    count = 1

    match sys_platform.system():
        case "Linux":
            ping_cmd = f"ping -W {timeout} -c {count} {ip_address}"
        case "Windows":
            ping_cmd = f"ping -w {timeout} -n {count} {ip_address}"
        case other:
            raise ValueError(f"Unsupported operating system: {other}")

    try:
        shell_out(
            command=ping_cmd,
            print_input=False,
            print_output=False,
        )
    except subprocess.CalledProcessError:
        return False

    return True
