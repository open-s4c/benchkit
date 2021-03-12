# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Definition of the types related to dependencies.
"""

import itertools
from typing import Iterable

from benchkit.dependencies.packagemanagers import PackageManager
from benchkit.platforms import Platform, get_current_platform

Dependencies = Iterable["Dependency"] | None


class Dependency:
    """
    Represent a single dependency, that can be a package, a binary program, etc.
    """

    def __init__(
        self,
        dependencies: Dependencies,
        platform: Platform | None,
    ) -> None:
        self.dependencies = dependencies if dependencies is not None else []
        self.platform = platform if platform is not None else get_current_platform()

    @property
    def name(self) -> str:
        """
        Get name of the dependency.

        Returns:
            str: name of the dependency.
        """
        raise NotImplementedError()

    def package_name(
        self,
        package_manager: PackageManager,
    ) -> str:
        """
        Get name of the package related to the dependency.

        Args:
            package_manager (PackageManager): package manager used to find package name.

        Returns:
            str: name of the package related to the dependency.
        """
        raise NotImplementedError()

    def present(self) -> bool:
        """
        Return whether the dependency is present on the given system.

        Returns:
            bool: whether the dependency is present on the given system.
        """
        raise NotImplementedError()

    def absent(self) -> bool:
        """Return whether the dependency is absent on the given system.

        Returns:
            bool: whether the dependency is absent on the given system.
        """
        return not self.present()

    def all_presents(self) -> bool:
        """
        Return whether the dependency and all its dependencies (recursively) are presents on the
        given system.

        Returns:
            bool:
                whether the dependency and all its dependencies (recursively) are presents on the
                given system.
        """
        result = True
        for dependency in self.dependencies:
            result = result and dependency.all_presents()
            if not result:
                return False
        result = result and self.present()
        return result

    def absents(self) -> Iterable["Dependency"]:
        """
        Return the list of absents dependencies from the current dependency and its own dependencies
        (recursively).

        Returns:
            Iterable[Dependency]:
                the list of absents dependencies from the current dependency and its own
                dependencies (recursively).
        """
        absent_current = [[self]] if self.absent() else []
        absent_dep_lists = [d.absents() for d in self.dependencies] + absent_current
        result = itertools.chain(*absent_dep_lists)
        return result
