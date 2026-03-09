# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import inspect

class Programmer:
    """"
    This is an interface for a programmer, which can be used to flash a binary
    to a device, reset the device, start the device, and stop the device. The
    actual implementation of these methods will depend on the specific
    programmer being used.kjq:
    """
    def flash(self, bin: pathlib.Path, addr: str) -> None: ...
    def reset(self) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...

    def with_features(self, features: list[str]) -> "Programmer":
        methods: set[str] = set(inspect.getmembers(self.__class__, predicate=inspect.isroutine))
        to_remove: set[str] = methods - set(features)

        if len(to_remve) != len(methods) - len(features):
            raise ValueError(f"Some features in {features} are not valid for {self.__class__.__name__}")

        def blank(*args, **kwargs):
            raise NotImplementedError(f"{feature} is not implemented for {self.__class__.__name__}")

        for feature in to_remove: 
            setattr(self, feature, blank)

        return self
