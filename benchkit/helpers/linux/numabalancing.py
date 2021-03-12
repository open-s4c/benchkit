# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interact with NUMA balancing daemon on Linux.
"""

from benchkit.communication import CommunicationLayer, LocalCommLayer
from benchkit.helpers.linux import sysctl
from benchkit.platforms import Platform

_VARIABLE_STRING = "kernel.numa_balancing"


def _get_comm_layer(platform: Platform | None = None) -> CommunicationLayer:
    if platform is None:
        return LocalCommLayer()
    return platform.comm


def is_enabled(platform: Platform | None = None) -> bool:
    """Return whether NUMA balancing daemon is enabled on given platform.

    Args:
        platform (Platform | None, optional):
            the platform to query. If None, take the local host platform. Defaults to None.

    Raises:
        ValueError: if kernel.numa_balancing has an unsupported value.

    Returns:
        bool: whether NUMA balancing daemon is enabled on given platform.
    """
    comm_layer = _get_comm_layer(platform=platform)
    output = sysctl.read(
        variable=_VARIABLE_STRING,
        comm_layer=comm_layer,
    ).strip()
    match output:
        case "0":
            return False
        case "1":
            return True
        case _:
            raise ValueError(f'Unknown returned value for sysctl kernel.numa_balancing: "{output}"')


def disable(platform: Platform | None = None) -> None:
    """Disable the NUMA balancing daemon on the given platform.

    Args:
        platform (Platform | None, optional):
            the platform where to disable the daemon. If None, take the local host platform.
            Defaults to None.
    """
    comm_layer = _get_comm_layer(platform=platform)
    if is_enabled(platform=platform):
        sysctl.write(
            variable=_VARIABLE_STRING,
            value="0",
            comm_layer=comm_layer,
        )


def enable(platform: Platform | None = None) -> None:
    """Enable the NUMA balancing daemon on the given platform.

    Args:
        platform (Platform | None, optional):
            the platform where to enable the daemon. If None, take the local host platform.
            Defaults to None.
    """
    comm_layer = _get_comm_layer(platform=platform)
    if not is_enabled(platform=platform):
        sysctl.write(
            variable=_VARIABLE_STRING,
            value="1",
            comm_layer=comm_layer,
        )
