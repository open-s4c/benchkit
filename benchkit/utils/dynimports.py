# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to import modules dynamically from their name.
"""

import importlib.util
import sys

from benchkit.utils.types import PathType


def import_dynamically(
    module_name: str,
    path: PathType,
) -> None:
    """
    Import the given module dynamically from the given path.

    Args:
        module_name (str): name of the module to import.
        path (PathType): path where to look for the module.
    """
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    dyn_class = sys.modules[module_name].get_bench_class()
    return dyn_class
