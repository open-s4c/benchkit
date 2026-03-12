# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.platforms import Platform

import pathlib
import inspect

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
        Get the platform that this flasher is designed for
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
            addr: The address to flash the binary to (e.g., "0x080000
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

    def with_features(self, features: list[str]) -> "Flasher":
        """
        Return a new instance of the flasher with only the specified features
        implemented. As not all flashers, MCUs, ... support all features,
        this allows us to create a flasher that only implements the features
        that are supported by the underlying hardware and software.
        """

        methods: set[str] = set(inspect.getmembers(self.__class__, predicate=inspect.isroutine))
        to_remove: set[str] = methods - set(features)

        if len(to_remve) != len(methods) - len(features):
            raise ValueError(f"Some features in {features} are not valid for {self.__class__.__name__}")

        # HACK this is a bit hacky, but it allows us to easily remove methods from the programmer
        def blank(*args, **kwargs):
            raise NotImplementedError(f"{feature} is not implemented for {self.__class__.__name__}")

        for feature in to_remove: 
            setattr(self, feature, blank)

        return self
