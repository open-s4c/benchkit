# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

class StatusAware:
    """
    Abstract class for communication layers that are aware of their connection status.
    """


    def is_open(self) -> bool:
        """
        Returns whether the communication layer is open.
        """
        ...


    def start_comm(self) -> None:
        """
        Starts the communication layer.
        """
        ...


    def close_comm(self) -> None:
        """
        Performs checks then, closes the communication layer.
        """
        ...


    def _unchecked_close_comm(self) -> None:
        """
        Closes the communication layer without checking whether it is open.
        """
        ...
