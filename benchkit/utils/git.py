# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities to manipulate git repositories.
"""

from benchkit.utils.types import PathType
import os
import git


def clone_repo(
    repo_url: str,
    repo_src_dir: PathType,
    tag: str = "",
    commit: str = "",
) -> None:
    """Clone given repository in the given directory and point to the given tag or the given commit."""

    if tag and commit:
        raise ValueError("tag and commit cannot be specified at the same time")

    if not repo_src_dir.is_dir():
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
        if commit:
            repo.git.checkout(commit)
