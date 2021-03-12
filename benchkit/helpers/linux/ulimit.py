# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interact (read/write) with `ulimit` variables.
"""

import sys

from benchkit.communication import CommunicationLayer, LocalCommLayer


def _command(
    soft_limit_type: bool | None,
    option: str,
) -> str:
    limit_type_s = {
        True: "-S",
        False: "-H",
        None: "",
    }.get(soft_limit_type)
    option_s = f"-{option}"

    command = f"ulimit {limit_type_s} {option_s}"

    return command


def _read(
    soft_limit_type: bool | None,
    option: str,
    comm_layer: CommunicationLayer = LocalCommLayer(),
) -> str:
    command = _command(soft_limit_type=soft_limit_type, option=option)
    output = comm_layer.shell(
        command=command,
        shell=True,
        print_input=False,
        print_output=False,
    ).strip()
    return output


def _write(
    soft_limit_type: bool | None,
    option: str,
    value: int,
    comm_layer: CommunicationLayer = LocalCommLayer(),
) -> None:
    command_prefix = _command(soft_limit_type=soft_limit_type, option=option)
    command = f"{command_prefix} {value}"
    output = comm_layer.shell(
        command=command,
        shell=True,
        print_input=False,
        print_output=False,
    ).strip()
    print(output)


def get_file_descriptor_count(
    soft_limit_type: bool | None,
    comm_layer: CommunicationLayer = LocalCommLayer(),
) -> str:
    """Get the file descriptor count from ulimit.

    Args:
        soft_limit_type (bool | None):
            whether the limit type is soft or not. None does not specify it.
        comm_layer (CommunicationLayer, optional):
            Communication layer of the host to query.
            Defaults to LocalCommLayer().

    Returns:
        str: the file descriptor count from ulimit.
    """
    value = _read(
        soft_limit_type=soft_limit_type,
        option="n",
        comm_layer=comm_layer,
    )
    return value


def set_file_descriptor_count(
    soft_limit_type: bool | None,
    value: int = 8192,
    comm_layer: CommunicationLayer = LocalCommLayer(),
) -> None:
    """Set the file descriptor count from ulimit.

    Args:
        soft_limit_type (bool | None):
            whether the limit type is soft or not. None does not specify it.
        value (int, optional):
            the value to set to the file descriptor count. Defaults to 8192.
        comm_layer (CommunicationLayer, optional):
            Communication layer of the host to query.
            Defaults to LocalCommLayer().

    Raises:
        ValueError: if setting the count failed.
    """
    current_value = get_file_descriptor_count(
        soft_limit_type=soft_limit_type,
        comm_layer=comm_layer,
    )
    if current_value != value:
        _write(
            soft_limit_type=soft_limit_type,
            option="n",
            value=value,
            comm_layer=comm_layer,
        )
        current_value = get_file_descriptor_count(
            soft_limit_type=soft_limit_type,
            comm_layer=comm_layer,
        )
        if str(current_value) != str(value):
            raise ValueError(
                "Impossible to set file descriptor count: "
                f'expected to set "{value}", actual is "{current_value}"'
            )


def ensure_permanent_file_descriptor_count(
    soft_limit_type: bool,
    value: int,
    comm_layer: CommunicationLayer = LocalCommLayer(),
) -> None:
    """Ensure the file descriptor count remains permanent even after rebooting the host.

    Args:
        soft_limit_type (bool):
            whether the limit type is soft or not. None does not specify it.
        value (int):
            the value to set to the file descriptor count.
        comm_layer (CommunicationLayer, optional):
            Communication layer of the host to query.
            Defaults to LocalCommLayer().
    """
    user = comm_layer.current_user()
    limit_type = "soft" if soft_limit_type else "hard"
    item = "nofile"

    line = f"{user:<17}{limit_type:<8}{item:<16}{value}"

    limits_filename = "/etc/security/limits.conf"
    file_content = comm_layer.read_file(limits_filename).splitlines()
    if line not in file_content:
        print(
            f'[WARNING] Please add the following line to "{limits_filename}" and reboot:\n{line}',
            file=sys.stderr,
        )
        raise SystemExit(1)
