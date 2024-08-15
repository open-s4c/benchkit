# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities to interact with system.

TODO deprecate in favor of platforms/comm layer
"""

import platform as sys_platform


def _get_linux_boot_args() -> str:
    with open("/proc/cmdline", "r") as cmdline:
        boot_args = cmdline.read().strip()
    return boot_args


def _get_windows_boot_args() -> str:
    return "<boot args fetching is unsupported on Windows>"

def _get_netbsd_boot_args() -> str:
    return "<boot args fetching is unsupported on NetBSD>"


def get_boot_args() -> str:
    """
    Return the boot arguments used on the currently running kernel.

    Raises:
        ValueError: if the current operating system is neither Linux nor Windows.

    Returns:
        str: the boot arguments used on the currently running kernel.
    """
    match sys_platform.system():
        case "Linux":
            result = _get_linux_boot_args()
        case "Windows":
            result = _get_windows_boot_args()
        case "NetBSD":
            result = _get_netbsd_boot_args()
        case other:
            raise ValueError(f"Unsupported operating system: {other}")
    return result
