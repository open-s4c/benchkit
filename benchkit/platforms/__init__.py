# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
The platform module allows to manipulate and retrieve all sort of information about platforms where
benchmarks are running such as the number of CPUs, the size of the cache groups, etc.
In particular, a Platform is initialized with a CommunicationLayer ensuring that the benchkit host
is able to run remote command on the target where the benchmark will run.
"""

import importlib.util
import sys

from benchkit.communication import LocalCommLayer, SSHCommLayer
from benchkit.platforms.generic import Platform
from benchkit.platforms.register import get_registered_platform
from benchkit.utils.types import Environment

if importlib.util.find_spec("deephierarchy") is None:
    _DEEPHIERARCHY_ENABLED = False
else:
    # optional external library that manage the deep memory hierarchy
    # including cache groups, NUMA nodes, etc.:
    import deephierarchy  # pylint: disable=import-error

    _DEEPHIERARCHY_ENABLED = True


def get_current_platform() -> Platform:
    """
    Get an instance of platform corresponding to the local host machine where benchkit is running.

    Returns:
        Platform: an instance of platform corresponding to the local machine where benchkit is
        running.
    """
    platform = get_registered_platform()
    if platform is not None:
        return platform

    if _DEEPHIERARCHY_ENABLED:
        platform = deephierarchy.ensure_deephierarchy_headers(
            force_install=False,
            use_benchkit_platform=False,
            use_installed_headers=True,
        )
        return platform

    print(
        (
            "[WARNING] Host machine not registered with hostname, "
            "and deephierarchy module not found. "
            "Defaulting to generic platform."
        ),
        file=sys.stderr,
    )
    return Platform(comm_layer=LocalCommLayer())


def get_remote_platform(
    host: str,
    environment: Environment = None,
) -> Platform:
    """
    Get a Platform instance corresponding to the provided SSH host.

    Args:
        host (str):
            name of the host (according to SSH configuration) for which to create the Platform
            instance.
        environment (Environment, optional):
            Environment variables to pass to each remote command executed on the provided host.
            Defaults to None.

    Returns:
        Platform: _description_
    """
    platform = get_registered_platform(machine_name=host, remote=True, environment=environment)
    if platform is not None:
        return platform

    print(
        (
            "[WARNING] Remote host machine not registered with hostname, "
            "defaulting to generic platform."
        ),
        file=sys.stderr,
    )
    return Platform(
        comm_layer=SSHCommLayer(
            host=host,
            environment=environment,
        )
    )
