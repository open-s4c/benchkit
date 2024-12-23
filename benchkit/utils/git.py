# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities to manipulate git repositories.
"""


import os
import pathlib
from typing import Iterable

import git

from benchkit.utils.types import PathType


def clone_repo(
    repo_url: str,
    repo_src_dir: PathType,
    tag: str = "",
    commit: str = "",
    modules: bool = False,
    patches: Iterable[PathType] = (),
) -> None:
    """
    Clone a Git repository into a specified directory and optionally check out
    a specific tag or commit.

    Args:
        repo_url (str):
            URL of the Git repository to clone.
        repo_src_dir (PathType):
            Path to the local directory where the repository should be cloned.
            If the directory does not exist, it will be created.
        tag (str, optional):
            Specific Git tag to check out after cloning.
            Cannot be set if `commit` is specified.
        commit (str, optional):
            Specific Git commit hash to check out after cloning.
            Cannot be set if `tag` is specified.
        modules (bool, optional):
            Recursively init submodules (default: False).
        patches (Iterable[PathType], optional):
            Apply all the provided patches (default: ()).

    Raises:
        ValueError:
            If both `tag` and `commit` are provided.
    """

    if tag and commit:
        raise ValueError("tag and commit cannot be specified at the same time")

    repo_src_dir = pathlib.Path(repo_src_dir)
    repo_was_there = repo_src_dir.is_dir()
    if not repo_was_there:
        os.makedirs(repo_src_dir, exist_ok=False)

        if tag:
            repo = git.Repo.clone_from(
                url=repo_url,
                to_path=repo_src_dir,
                branch=tag,
            )
        else:
            repo = git.Repo.clone_from(
                url=repo_url,
                to_path=repo_src_dir,
            )
    else:
        repo = git.Repo(path=repo_src_dir)

    if tag:
        repo.git.checkout(tag)
    if commit:
        repo.git.checkout(commit)

    if modules:
        repo.git.submodule("update", "--init", "--recursive")

    if repo_was_there:
        return

    for patch in patches:
        print(patch)
        repo.git.apply(patch)
        repo.git.add("-u")
