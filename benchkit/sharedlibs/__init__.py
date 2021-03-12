# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interface with shared libraries, that can possibly be loaded using LD_PRELOAD environment variable.
"""

import pathlib
from typing import List, Tuple

from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import get_current_platform
from benchkit.utils.types import EnvironmentVariables, LdPreloadLibraries, PathType


class SharedLib:
    """
    Represent a shared library.
    """

    def __init__(self):
        self.platform = get_current_platform()

    def dependencies(self) -> List[PackageDependency]:
        """
        Get the dependencies of the shared library.

        Returns:
            List[PackageDependency]: the dependencies of the shared library.
        """
        return []

    def configure(self) -> None:
        """
        Configure the build of the shared library.
        """

    def preload(self, **_kwargs) -> Tuple[LdPreloadLibraries, EnvironmentVariables]:
        """
        Pre-load the shared library using LD_PRELOAD.

        Returns:
            Tuple[LdPreloadLibraries, EnvironmentVariables]:
                tuple t, such that t[0] is the libraries to preload and t[1] are the environment
                variables.
        """
        return [], {}

    def must_debug(self) -> bool:
        """
        Return whether the libraries must be built with debug mode enabled.

        Returns:
            bool: whether the libraries must be built with debug mode enabled.
        """
        return False


class FromSourceSharedLib(SharedLib):
    """
    Shared library that must be compiled from sources.
    """

    def __init__(
        self,
        src_path: PathType,
        debug_mode: bool,
    ) -> None:
        super().__init__()

        self.src_path = pathlib.Path(src_path)
        self.build_dir = self.src_path / f"build-{self.platform.hostname}"
        self._debug_mode = debug_mode

    def preload(
        self,
        **kwargs,
    ) -> Tuple[LdPreloadLibraries, EnvironmentVariables]:
        ld_preloads, env_vars = super().preload(
            **kwargs,
        )

        return ld_preloads, env_vars

    def must_debug(self) -> bool:
        return self._debug_mode
