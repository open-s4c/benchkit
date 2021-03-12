# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Management of dependencies of benchkit components.
This module provides primitive to check that dependencies are present or absent.
When missing, an error message instructs the user of how to install them.
"""

import itertools
import platform as sys_platform
import sys
from typing import Iterable, List

from benchkit.dependencies.dependency import Dependency
from benchkit.dependencies.packagemanagers import get_package_manager
from benchkit.platforms import Platform


def all_absents(all_dependencies: Iterable[Dependency]) -> List[Dependency]:
    """
    Get all the packages that are missing (absents, not presents) from the provided collection of
    dependencies.

    Args:
        all_dependencies (Iterable[Dependency]): an iterable of all the dependencies to check.

    Returns:
        List[Dependency]: list of dependencies that are missing (absents, non presents).
    """
    absent_dep_lists = [d.absents() for d in all_dependencies]
    iterator = itertools.chain(*absent_dep_lists)
    result = list(iterator)
    return result


def check_dependencies(
    all_dependencies: Iterable[Dependency],
    platform: Platform,
) -> None:
    """
    Check that all the given dependencies are met on the given platform.
    If they are not, exit with an error message telling how to install the missing dependencies.

    Args:
        all_dependencies (Iterable[Dependency]): _description_
        platform (Platform): _description_
    """
    if "Linux" != sys_platform.system():
        return

    absent_dependencies = all_absents(all_dependencies=all_dependencies)

    if not absent_dependencies:
        return

    package_mgr = get_package_manager(platform=platform)

    missing_packages = [
        missing_package
        for absent_dependency in absent_dependencies
        if (missing_package := absent_dependency.package_name(package_manager=package_mgr))
        is not None
    ]
    missing_files = [
        absent_dependency.name
        for absent_dependency in absent_dependencies
        if absent_dependency.package_name(package_manager=package_mgr) is None
    ]

    package_line = package_mgr.get_install_lines(packages=missing_packages)
    package_line_s = "\n    ".join(package_line)
    missing_line_s = " ".join(missing_files)

    packages_err = (
        [f"To install all dependencies needed by this benchmark:\n    {package_line_s}"]
        if missing_packages
        else []
    )
    files_err = (
        [f"Please find a way to install the following programs & libs:\n    {missing_line_s}"]
        if missing_files
        else []
    )

    errors = packages_err + files_err
    err_msg = "\n\n".join(errors)

    print(err_msg, file=sys.stderr)
    raise SystemExit(1)
