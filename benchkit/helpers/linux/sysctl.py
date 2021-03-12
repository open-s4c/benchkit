# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interact (read/write) with `sysctl` variables.
"""

from benchkit.communication import CommunicationLayer


def read(
    variable: str,
    comm_layer: CommunicationLayer,
) -> str:
    """Read the given variable in `sysctl` on the provided host.

    Args:
        variable (str): name of the variable to read.
        comm_layer (CommunicationLayer): communication layer on the host to query.

    Returns:
        str: value of the variable read.
    """
    sysctl_command = ["sysctl", "-n", f"{variable}"]
    command = sysctl_command
    output = comm_layer.shell(command=command, print_input=False, print_output=False).strip()
    return output


def write(
    variable: str,
    value: str,
    comm_layer: CommunicationLayer,
) -> None:
    """Write the given value to the given variable in `sysctl` on the provided host.

    Args:
        variable (str): name of the variable to write.
        value (str): value of the variable to write.
        comm_layer (CommunicationLayer): communication layer on the host to query.
    """
    sysctl_command = ["sysctl", "-w", f"{variable}={value}"]
    command = ["sudo"] + sysctl_command
    comm_layer.shell(command=command)


def get_kernel_perf_event_paranoid(
    comm_layer: CommunicationLayer,
) -> int:
    """Get the value of the `kernel.perf_event_paranoid` variable on the given host.

    Args:
        comm_layer (CommunicationLayer): communication layer on the host to query.

    Returns:
        int: _description_
    """
    output = read(variable="kernel.perf_event_paranoid", comm_layer=comm_layer)
    result = int(output)
    return result


def set_kernel_perf_event_paranoid(
    value: int,
    comm_layer: CommunicationLayer,
) -> None:
    """Set the value of the `kernel.perf_event_paranoid` variable on the given host.

    Args:
        value (int): value to set to the variable.
        comm_layer (CommunicationLayer): communication layer on the host to query.

    Raises:
        ValueError: if the value is outside [-1,4].
    """
    if value > 4 or value < -1:
        raise ValueError(f"Given value for kernel.perf_event_paranoid out of range: {value}")
    write(variable="kernel.perf_event_paranoid", value=str(value), comm_layer=comm_layer)
