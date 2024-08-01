# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities related to platform modules.
"""

import os
from typing import Set

from benchkit.communication import CommunicationLayer


def _parse_list_ranges(list_ranges: str) -> Set[int]:
    result_set = set()

    elements = list_ranges.split(",")
    for element in elements:
        if "-" in element:
            low, high = [int(e) for e in element.split("-")]
            for elem in range(low, high + 1):
                result_set.add(elem)
        elif element.isdigit():
            result_set.add(int(element))

    return result_set


def get_nb_cpus_total(comm_layer: CommunicationLayer) -> int:
    """
    Get the total number of CPUs of the provided host (including the isolated ones).
    The function uses 2 different sources to validate the number is correct.

    Args:
        comm_layer (CommunicationLayer): communication layer of the provided host.

    Raises:
        ValueError: if the two sources return different values.

    Returns:
        int: the total number of CPUs of the provided host.
    """
    # Try different commands to get the amount of CPUs
    try:
        # Linux
        result1 = int(
            comm_layer.shell(
                command="nproc --all",
                print_input=False,
                print_output=False,
            ).strip()
        )
    except FileNotFoundError:
        try:
            # Darwin
            result1 = int(
                comm_layer.shell(
                    command="sysctl -n hw.ncpu",
                    print_input=False,
                    print_output=False,
                ).strip()
            )
        except FileNotFoundError:
            # Windows
            result1 =  int(
                comm_layer.shell(
                    command="wmic cpu get numberofcores",
                    print_input=False,
                    print_output=False,
                ).strip().split()[1])
    
    if comm_layer.is_local:
        result2 = os.cpu_count()
        if result1 != result2:
            raise ValueError("Problem with CPU counting on current platform.")

    return result1


def get_nb_cpus_isolated(comm_layer: CommunicationLayer) -> int:
    """Get the number of CPUs that are currently isolated on the provided host.

    Args:
        comm_layer (CommunicationLayer): communication layer of the provided host.

    Returns:
        int: the number of CPUs that are currently isolated on the provided host.
    """
    # Some operating systems might not provide this information
    try:
        isolated_str = comm_layer.read_file("/sys/devices/system/cpu/isolated").strip()
    except FileNotFoundError:
        return 0
        
    isolated_cpus = _parse_list_ranges(list_ranges=isolated_str)

    return len(isolated_cpus)


def get_nb_cpus_active(comm_layer: CommunicationLayer) -> int:
    """Get the number of CPUs that are currently active (not isolated) on the provided host.

    Args:
        comm_layer (CommunicationLayer): communication layer of the provided host.

    Returns:
        int: the number of CPUs that are currently active on the provided host.
    """
    nb_cpus_isolated = get_nb_cpus_isolated(comm_layer=comm_layer)
    nb_cpus_total = get_nb_cpus_total(comm_layer=comm_layer)
    nb_cpus_active = nb_cpus_total - nb_cpus_isolated

    return nb_cpus_active
