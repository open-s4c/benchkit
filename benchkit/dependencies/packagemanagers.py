# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interactions with package managers on platforms.
"""

from typing import Iterable, List

from benchkit.platforms import Platform

_apt_file2package = {
    "cmake": "cmake",
    "nmap": "nmap",
}

_dnf_file2package = {}

_pacman_file2package = {}

class PackageManager:
    """
    Represent a package manager and the primitives to check existence, check presence and
    installation of packages.
    """

    def filename_to_packagename(
        self,
        filename: str,
    ) -> str:
        """
        Convert a file name into the corresponding package name on the current package manager.

        Args:
            filename (str): name of the file to convert into a package name.

        Returns:
            str: the name of the package corresponding to the given filename.
        """
        raise NotImplementedError()

    def get_install_lines(
        self,
        packages: Iterable[str],
    ) -> List[str]:
        """
        Get the command to install the given packages.

        Args:
            packages (Iterable[str]):
                a collection of packages for which to get the installation command line.

        Returns:
            List[str]: the command to install the given packages.
        """
        raise NotImplementedError()

    def package_exists(
        self,
        package_name: str,
        platform: Platform,
    ) -> bool:
        """
        Return whether the given package exists on the given platform.
        The current package manager is used to check.

        Args:
            package_name (str): name of the package to check.
            platform (Platform): platform on which to check that the given package exists.

        Returns:
            bool: whether the given package exists on the given platform.
        """
        raise NotImplementedError()

    def package_is_installed(
        self,
        package_name: str,
        platform: Platform,
    ) -> bool:
        """
        Return whether the provided package is installed on the given platform.
        It is checked with the current package manager primitives.

        Args:
            package_name (str): name of the package to find in the package manager.
            platform (Platform): platform to which to check that the package is installed.

        Returns:
            bool: whether the provided package is installed on the given platform.
        """
        raise NotImplementedError()


class Apt(PackageManager):
    """
    Represent the "apt" package manager, installed on debian-based distribution.
    """

    def filename_to_packagename(
        self,
        filename: str,
    ) -> str | None:
        return _apt_file2package.get(filename)

    def get_install_lines(
        self,
        packages: Iterable[str],
    ) -> List[str]:
        packages_s = " ".join(packages)
        return [
            "sudo apt update",
            f"sudo apt install -y {packages_s}",
        ]

    def package_exists(
        self,
        package_name: str,
        platform: Platform,
    ) -> bool:
        expected_package = package_name

        command = f"apt-cache search --names-only ^{expected_package}$"
        output = platform.comm.shell(
            command=command,
            print_input=False,
            print_output=False,
        ).strip()

        actual_package, *_ = output.split(" - ")
        result = expected_package == actual_package

        return result

    def package_is_installed(
        self,
        package_name: str,
        platform: Platform,
    ) -> bool:
        return platform.comm.shell_succeed(
            command=f"dpkg --status {package_name}",
            print_input=False,
            print_output=False,
        )


class Dnf(PackageManager):
    """
    Represent the "dnf" package manager, installed on redhat-based distribution.
    """

    def filename_to_packagename(
        self,
        filename: str,
    ) -> str | None:
        return _dnf_file2package.get(filename)

    def get_install_lines(
        self,
        packages: Iterable[str],
    ) -> List[str]:
        packages_s = " ".join(packages)
        return [f"dnf install -y {packages_s}"]

    def package_exists(
        self,
        package_name: str,
        platform: Platform,
    ) -> bool:
        return platform.comm.shell_succeed(
            command=f"dnf list {package_name}",
            print_input=False,
            print_output=False,
        )

    def package_is_installed(
        self,
        package_name: str,
        platform: Platform,
    ) -> bool:
        return platform.comm.shell_succeed(
            command=f"dnf list installed {package_name}",
            print_input=False,
            print_output=False,
        )

class Pacman(PackageManager):
    """
    Represent the "pacman" package manager, installed on arch-based 
    distributions such as Manjaro and Arch."
    """

    def filename_to_packagename(
        self,
        filename: str,
    ) -> str | None:
        return _pacman_file2package.get(filename)

    def get_install_lines(
        self,
        packages: Iterable[str],
    ) -> List[str]:
        packages_s = " ".join(packages)
        return [f"pacman -Syu {packages_s}"]

    def package_exists(
        self,
        package_name: str,
        platform: Platform,
    ) -> bool:
        # This command uses a regex to get an exact match to see if 
        # the given package exists.
        return platform.comm.shell_succeed(
            command=f"pacman -Ss ^{package_name}$",
            print_input=False,
            print_output=False,
        )

    def package_is_installed(
        self,
        package_name: str,
        platform: Platform,
    ) -> bool:
        return platform.comm.shell_succeed(
            command=f"pacman -Q {package_name}",
            print_input=False,
            print_output=False,
        )


def get_package_manager(platform: Platform) -> PackageManager:
    """
    Return the package manager installed on the given platform.

    Args:
        platform (Platform): the platform on which to find the installed package manager.

    Raises:
        ValueError: the package manager installed on the given platform.

    Returns:
        PackageManager: _description_
    """
    apt = platform.comm.which(cmd="apt")
    if apt is not None:
        return Apt()

    dnf = platform.comm.which(cmd="dnf")
    if dnf is not None:
        return Dnf()
    
    pacman = platform.comm.which(cmd="pacman")
    if pacman is not None:
        return Pacman()

    raise ValueError("Supported package manager not found")
