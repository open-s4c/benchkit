# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Dependencies that represent packages.
Are supported: packages, kernel modules and direct dependency to Docker.
"""

from benchkit.dependencies.dependency import Dependencies, Dependency
from benchkit.dependencies.packagemanagers import PackageManager, get_package_manager
from benchkit.platforms import Platform


class PackageDependency(Dependency):
    """
    Represent a dependency to a package.
    """

    def __init__(
        self,
        name: str,
        dependencies: Dependencies = None,
        platform: Platform | None = None,
    ) -> None:
        super().__init__(
            dependencies=dependencies,
            platform=platform,
        )

        self._name = name
        self._in_repositories = True
        self._package_manager = None

    @property
    def name(self) -> str:
        """
        Get the name of the package.

        Returns:
            str: the name of the package.
        """
        return self._name

    @property
    def package_manager(self) -> PackageManager:
        """
        Return the package manager corresponding to the current package dependency.

        Returns:
            PackageManager: the package manager corresponding to the current package dependency.
        """
        if self._package_manager is None:
            self._package_manager = get_package_manager(platform=self.platform)
        return self._package_manager

    def package_name(
        self,
        package_manager: PackageManager,
    ) -> str:
        return self.name

    def present(self) -> bool:
        result = not self.exists() or self.is_installed()
        return result

    def exists(self) -> bool:
        """
        Return whether the package exist in the package manager of the platform.

        Returns:
            bool: whether the package exist in the package manager of the platform.
        """
        pkg_mgr = self.package_manager
        package_name = self.package_name(package_manager=pkg_mgr)
        result = pkg_mgr.package_exists(package_name=package_name, platform=self.platform)
        return result

    def is_installed(self) -> bool:
        """
        Return whether the package is installed on the platform.

        Returns:
            bool: whether the package is installed on the platform.
        """
        pkg_mgr = self.package_manager
        package_name = self.package_name(package_manager=pkg_mgr)
        result = pkg_mgr.package_is_installed(package_name=package_name, platform=self.platform)
        return result


class KernelModuleDependency(PackageDependency):
    """Represent a dependency to kernel module."""

    def __init__(
        self,
        name: str,
        dependencies: Dependencies = None,
        platform: Platform | None = None,
    ):
        super().__init__(
            name=name,
            dependencies=dependencies,
            platform=platform,
        )

    def present(self) -> bool:
        return self.platform.comm.shell_succeed(
            command=f"modinfo {self.name}",
            print_output=False,
            print_input=False,
        )


class DockerDependency(PackageDependency):
    """
    Represent the dependency to Docker (check that the module is loaded).
    """

    def __init__(
        self,
        dependencies: Dependencies = None,
        platform: Platform | None = None,
    ):
        super().__init__(
            name="docker",
            dependencies=dependencies,
            platform=platform,
        )

    def present(self) -> bool:
        return self.platform.comm.shell_succeed(
            command=f"modinfo {self.name}",
            print_output=False,
            print_input=False,
        )
