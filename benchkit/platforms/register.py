# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to retrieve the registered platforms from a register file.
It assumes a file with the mapping between hostname and platform typess is provided, called
"registerfile.py".
"""

import importlib
import pathlib
from typing import Dict, Type

from benchkit.communication import LocalCommLayer, SSHCommLayer
from benchkit.platforms.generic import Platform
from benchkit.utils.misc import hostname
from benchkit.utils.types import Environment


def _get_hosts() -> Dict[str, Type[Platform]]:
    file = pathlib.Path(__file__)
    current_dir = file.parent.resolve()
    registerfilename = current_dir / "registerfile.py"

    if registerfilename.is_file():
        registerfile = importlib.import_module("benchkit.platforms.registerfile")
        result = registerfile.HOSTNAME_TO_PLATFORM
    else:
        result = {}

    return result


def get_registered_platform(
    machine_name: str | None = None,
    remote: bool = False,
    environment: Environment = None,
) -> Platform | None:
    """
    Get the platform from the register if the register is available and if the given hostname is in
    the register. Otherwise, return None.

    Args:
        machine_name (str | None, optional):
            The hostname of the machine to get a Platform for. Defaults to None.
        remote (bool, optional):
            Whether the platform is remote (not local). Defaults to False.
        environment (Environment, optional):
            Default environment to pass to every command executed on the Platform to instantiate.
            If None, no environment variable is systematically passed to each command the Platform
            executes.
            Defaults to None.

    Raises:
        ValueError:
            if the machine hostname is not provided for a remote machine.

    Returns:
        Platform | None:
            the platform from the register if the register is available and if the given hostname is
            in the register. Otherwise, return None.
    """
    hostname2platforms = _get_hosts()

    if remote:
        if machine_name is None:
            raise ValueError("For a remote machine, the machine name is required")
    else:
        if machine_name is None:
            machine_name = hostname()

    if machine_name not in hostname2platforms:
        return None

    comm_layer = (
        SSHCommLayer(host=machine_name, environment=environment) if remote else LocalCommLayer()
    )
    platform = hostname2platforms[machine_name](comm_layer=comm_layer)
    return platform
