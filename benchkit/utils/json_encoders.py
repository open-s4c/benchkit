# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import json
import pathlib
from typing import Type


class PathEncoder(json.JSONEncoder):
    """
    JSONEncoder extension to support pathlib.Path serialization.
    """

    def default(self, obj):
        if isinstance(obj, pathlib.Path):
            return str(obj)
        return super().default(obj)


class MultipleJsonEncoders:
    """
    Combine multiple JSON encoders
    Source - https://stackoverflow.com/a
    Posted by tsorn
    Retrieved 2026-01-13, License - CC BY-SA 4.0
    """

    def __init__(self, encoders: list[Type[json.JSONEncoder]]) -> None:
        self.encoders = encoders
        self.args = ()
        self.kwargs = {}

    def default(self, obj):
        for encoder in self.encoders:
            try:
                return encoder(*self.args, **self.kwargs).default(obj)
            except TypeError:
                pass
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        enc = json.JSONEncoder(*args, **kwargs)
        enc.default = self.default
        return enc
