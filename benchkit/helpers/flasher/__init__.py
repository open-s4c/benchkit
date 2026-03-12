# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib

from benchkit.platforms import Platform


class Flasher:
    """
    This is an interface for a flasher, which can be used to flash a binary
    to a device, reset the device, start the device, and stop the device. The
    actual implementation of these methods will depend on the specific
    flasher being used
    """

    @property
    def platform(self) -> Platform:
        """
        Get the platform to run the flasher on
        """
        ...

    def flash(
        self,
        bin: pathlib.Path,
        addr: str,
    ) -> None:
        """
        Flash the binary at the specified address.
        Args:
            bin: The path to the binary to flash.
            addr: The address to flash the binary to (e.g., "0x080000")
        """
        ...

    def reset(self) -> None:
        """
        Reset the device.
        """
        ...

    def start(self) -> None:
        """
        Start the device (e.g., by running it or exiting reset).
        """
        ...

    def stop(self) -> None:
        """
        Stop the device (e.g., by halting it or entering reset).
        """
        ...
