# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities to manipulate directories.
"""

import inspect
import os
import pathlib
from typing import Iterable

from benchkit.shell.shell import shell_out
from benchkit.utils.types import PathType


class FinddirNotFound(ValueError):
    """Error triggered when a directory is not found in a search."""


def get_curdir(current_filepath: PathType) -> pathlib.Path:
    """
    Return the current directory of the given file.

    Args:
        current_filepath (PathType):
            current_filepath file for which to retrieve the current directory.

    Returns:
        pathlib.Path: the current directory of the given file.
    """
    filepath = pathlib.Path(current_filepath)
    result = filepath.parent.resolve()
    return result


def parentdir(
    path: PathType,
    levels: int = 1,
) -> pathlib.Path:
    """
    Return the parent directory of the given path.

    Args:
        path (PathType):
            given path for which to retrieve the parent.
        levels (int, optional):
            number of levels to get the parent for.
            For example, 2 is the grand-parent.
            Defaults to 1.

    Returns:
        pathlib.Path: the parent directory of the given path.
    """
    result_path = pathlib.Path(path)
    for _ in range(levels):
        result_path = result_path.parent
    return result_path


def gitrootdir(path: PathType) -> pathlib.Path:
    """
    Return the path of the root directory of the git repository.

    Args:
        path (PathType):
            the current path from which to consider the git root directory.

    Returns:
        pathlib.Path: the path of the root directory of the git repository.
    """
    given_path = pathlib.Path(path)
    dir_path = given_path if given_path.is_dir() else given_path.parent
    output = shell_out(
        "git rev-parse --show-toplevel",
        current_dir=dir_path,
        print_input=False,
        print_output=False,
    ).strip()
    result = pathlib.Path(output)
    return result


def gitmainrootdir() -> pathlib.Path:
    """
    Same as gitrootdir, but it crosses the submodules.

    Returns:
        pathlib.Path: the root directory of the main git repository (not the submodules).
    """
    this_dir = parentdir(__file__)
    reldir = shell_out(
        command="git rev-parse --show-superproject-working-tree",
        current_dir=this_dir,
        print_input=False,
        print_output=False,
    ).strip()
    if not reldir:
        reldir = shell_out(
            command="git rev-parse --show-toplevel",
            current_dir=this_dir,
            print_input=False,
            print_output=False,
        ).strip()
    result = pathlib.Path(reldir).resolve()
    return result


def finddir(
    src_path: PathType,
    dir_name: str,
) -> pathlib.Path:
    """
    Find a directory with the name "dir_name" from the given source path.

    Args:
        src_path (PathType): path where to start the search.
        dir_name (str): name of the directory to find.

    Raises:
        FinddirNotFound: if the directory cannot be found in the source_path.

    Returns:
        pathlib.Path: the path to the found directory.
    """
    abspath = None
    for root, directories, _ in os.walk(src_path):
        if abspath is not None:
            break
        for directory in directories:
            if dir_name == directory:
                abspath = (pathlib.Path(root) / directory).resolve()
                if ".git" in str(abspath):
                    abspath = None
                else:
                    break

    if abspath is None:
        raise FinddirNotFound(f'Directory "{dir_name}" not found in "{src_path}"')

    return abspath


def finddir_in_paths(
    src_paths: Iterable[PathType],
    dir_name: str,
) -> PathType:
    """
    Find the given directory from several possible source paths.

    Args:
        src_paths (Iterable[PathType]):
            collection of paths to consider as source paths to start the search from.
        dir_name (str):
            name of the directory to find.

    Raises:
        FinddirNotFound: if the directory cannot be found in any of the source path.

    Returns:
        PathType: the path to the found directory.
    """
    abspath = None
    not_found_in = []

    for src_path in src_paths:
        try:
            abspath = finddir(src_path=src_path, dir_name=dir_name)
        except FinddirNotFound as err:
            not_found_in.append(str(err))

    if abspath is None:
        raise FinddirNotFound("\n".join(not_found_in))

    return abspath


def find_dependency_path(
    script_src_path: PathType,
) -> PathType:
    """
    Find the path to the directory where the dependencies are in the current git repository from the
    given script path.

    Args:
        script_src_path (PathType):
            the python file from which to start the search of the dependency path.

    Returns:
        PathType: the path to the found dependency directory.
    """
    git_root_path = gitrootdir(script_src_path)
    deps_path = None

    try:
        deps_path = finddir(src_path=git_root_path, dir_name="deps")
        found = True
        if "dependencies" in str(deps_path):
            found = False
    except FinddirNotFound:
        found = False

    if not found:
        deps_path = finddir(src_path=git_root_path, dir_name="dependencies")

    return deps_path


def find_specific_dependency(
    dependency_name: str,
) -> pathlib.Path:
    """
    Find the directory of the given dependency.

    Args:
        dependency_name (str): name of the dependency to find.

    Returns:
        pathlib.Path: path to the directory of the given dependency in the main git repository.
    """
    gmr = gitmainrootdir()
    deps_path = find_dependency_path(script_src_path=gmr)
    relpath = finddir_in_paths(src_paths=[deps_path], dir_name=dependency_name)
    path = pathlib.Path(os.path.abspath(relpath))
    return path


def caller_file_abs_path(
    nb_stack_frames: int = 1,
) -> pathlib.Path:
    """
    Return the absolute path of the file of the caller.

    Args:
        nb_stack_frames (int, optional):
            number of stack frames to climb to get to the caller module.
            Defaults to 1.

    Returns:
        pathlib.Path: the absolute path of the file of the caller.
    """
    stack = inspect.stack()
    # since we are in a function call, we need the caller of the caller:
    frame = stack[1 + nb_stack_frames]
    frame_filename = pathlib.Path(frame.filename)
    result = frame_filename.resolve()
    return result


def caller_dir() -> pathlib.Path:
    caller_filepath = caller_file_abs_path()
    caller_parent = caller_filepath.parent.resolve()
    return caller_parent
