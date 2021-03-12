# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to manage shared libraries that are already compiled.
Only the path to such a library must be provided to enable it.
"""

import os.path
import pathlib
from typing import List, Tuple

from benchkit.dependencies.packages import PackageDependency
from benchkit.sharedlibs import EnvironmentVariables, LdPreloadLibraries, SharedLib
from benchkit.utils.types import Environment, PathType


class PrecompiledSharedLib(SharedLib):
    """
    Represent a shared library that is already compiled.
    """

    def __init__(
        self,
        path: PathType,
        env_vars: Environment,
    ):
        super().__init__()
        self._path = pathlib.Path(os.path.abspath(path))
        self._env_vars = env_vars

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies()

    def preload(
        self,
        **kwargs,
    ) -> Tuple[LdPreloadLibraries, EnvironmentVariables]:
        ld_preloads, other_env_vars = super().preload(
            **kwargs,
        )

        if not self._path.is_file():
            raise ValueError(f"Impossible to find pre-compiled shared object file: {self._path}")

        ld_preloads.append(f"{self._path}")

        if self._env_vars is not None:
            other_env_vars.update(self._env_vars)

        return ld_preloads, other_env_vars
