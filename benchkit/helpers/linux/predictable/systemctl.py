# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interface with Linux systemd through `systemctl` command.
"""

from typing import Tuple

from benchkit.communication import CommunicationLayer, LocalCommLayer


class Systemctl:
    """Class to interact with system through `systemctl` command."""

    def __init__(
        self,
        comm_layer: CommunicationLayer = LocalCommLayer(),
    ) -> None:
        self._comm_layer = comm_layer

    def status(
        self,
        service_name: str,
    ) -> Tuple[bool, bool]:
        """Get the status of the given service.

        Args:
            service_name (str): name of the queried service.

        Returns:
            Tuple[bool, bool]: status of the queried service.
        """
        output = self._comm_layer.shell(
            command=f"systemctl status {service_name}",
            ignore_ret_codes=(3,),
            print_output=False,
        )
        output_lines = output.splitlines()

        enabled = "enabled" in output_lines[1]
        active = "inactive" not in output_lines[2]

        return enabled, active

    def is_active(
        self,
        service_name: str,
    ) -> bool:
        """Return whether the given service is active.

        Args:
            service_name (str): the name of the queried service.

        Returns:
            bool: whether the given service is active.
        """
        return self.status(service_name)[1]
