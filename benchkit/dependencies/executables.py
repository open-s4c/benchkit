# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Dependencies that represent executable programs (to be find in the path wich "which").
"""

import pathlib

from benchkit.dependencies.dependency import Dependencies, Dependency
from benchkit.dependencies.packagemanagers import PackageManager
from benchkit.platforms import Platform


class ExecutableDependency(Dependency):
    """
    Represent an executable program as a dependency, that must be present in the
    path (polled using "which").
    """

    def __init__(
        self,
        executable: str,
        dependencies: Dependencies = None,
        platform: Platform | None = None,
    ):
        super().__init__(
            dependencies=dependencies,
            platform=platform,
        )

        self._executable = executable

    @property
    def name(self) -> str:
        return self._executable

    def package_name(
        self,
        package_manager: PackageManager,
    ) -> str:
        return package_manager.filename_to_packagename(filename=self._executable)

    def present(self) -> bool:
        return self._resolvable()

    def _executable_path(self) -> pathlib.Path | None:
        exec_path = self.platform.comm.which(cmd=self._executable)
        return exec_path

    def _resolvable(self) -> bool:
        result = self._executable_path() is not None
        return result


def executable_is_installed(
    name: str,
    platform: Platform,
) -> bool:
    """Return whether the given executable is installed on given platform.

    Args:
        name (str): name of the executable to find.
        platform (Platform): platform where to check that the executable is installed.

    Returns:
        bool: whether the given executable is installed on given platform.
    """
    dep = ExecutableDependency(executable=name, platform=platform)
    return dep.present()
