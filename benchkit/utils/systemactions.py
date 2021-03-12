# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities to perform actions on the given system.

TODO deprecate in favor of commlayer/platforms.
"""

from benchkit.communication import CommunicationLayer, LocalCommLayer


def sync_filesystems(comm_layer: CommunicationLayer) -> None:
    """
    Run the "sync" command to flush all file systems of the target host.

    Args:
        comm_layer (CommunicationLayer): communication layer of the target host.
    """
    comm_layer.shell(command="sudo sync")


def drop_caches(comm_layer: CommunicationLayer) -> None:
    """
    Clean & invalidate all the caches of the target host.

    Args:
        comm_layer (CommunicationLayer): communication layer of the target host.
    """
    comm_layer.shell(
        command="sudo tee /proc/sys/vm/drop_caches",
        std_input="3",
    )


class DmesgLog:
    """
    Class to interact with kernel logs from "dmesg".
    """

    def __init__(
        self,
        comm_layer: CommunicationLayer = LocalCommLayer,
    ):
        self._comm_layer = comm_layer
        self.log = ""

    def __enter__(self):
        self._dmesg_clear()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log = self._dmesg_get()

    def _dmesg_clear(self) -> None:
        self._comm_layer.shell("sudo dmesg --clear")

    def _dmesg_get(self) -> str:
        return self._comm_layer.shell("sudo dmesg --color=never")
