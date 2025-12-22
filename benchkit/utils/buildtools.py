# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Common build utilities for benchmark implementations.

This module provides reusable helper functions for typical benchmark build operations:
- git_clone: Clone Git repositories with commit checkout
- make: Execute make with automatic parallelization
- build_dir_from_ctx: Generate platform-specific build directory paths

These utilities reduce code duplication across benchmark implementations and provide
sensible defaults (e.g., parallel make based on CPU count).
"""

from pathlib import Path

from benchkit.core.bktypes.contexts import BaseContext, BuildContext


def git_clone(
    ctx: BaseContext,
    url: str,
    commit: str,
    parent_dir: Path,
) -> Path:
    """
    Clone a Git repository and optionally check out a specific commit.

    If the repository already exists at the destination, skips cloning but
    still performs the checkout if a commit is specified.

    Args:
        ctx: Context providing platform and execution capabilities.
        url: Git repository URL (e.g., "https://github.com/user/repo.git").
        commit: Commit hash, tag, or branch to check out (empty string = don't checkout).
        parent_dir: Parent directory where the repository will be cloned.

    Returns:
        Path to the cloned repository directory.

    Example:
        >>> src_dir = git_clone(
        ...     ctx=fetch_ctx,
        ...     url="https://github.com/facebook/rocksdb.git",
        ...     commit="v10.7.5",
        ...     parent_dir=Path("/tmp/src"),
        ... )
    """
    platform = ctx.platform
    comm = platform.comm
    name = url.split("/")[-1].split(".")[0]
    dest = parent_dir / name

    if not comm.isdir(dest):
        if not comm.isdir(parent_dir):
            comm.makedirs(path=parent_dir, exist_ok=True)
        ctx.exec(argv=["git", "clone", f"{url}", f"{dest}"], cwd=parent_dir)

    if commit:
        ctx.exec(argv=["git", "checkout", f"{commit}"], cwd=dest)

    return dest


def make(
    ctx: BaseContext,
    src_dir: Path,
    targets: list[str],
    options: dict[str, str],
):
    """
    Execute make with automatic parallel job detection.

    Automatically adds -j flag with the number of active CPUs if more than one CPU
    is available. Build output is treated as log messages.

    Args:
        ctx: Context providing platform and execution capabilities.
        src_dir: Directory containing the Makefile.
        targets: List of make targets to build (e.g., ["all", "install"]).
        options: Dictionary of make variables (e.g., {"CC": "gcc", "CFLAGS": "-O3"}).

    Example:
        >>> make(
        ...     ctx=build_ctx,
        ...     src_dir=Path("/tmp/src/project"),
        ...     targets=["release"],
        ...     options={"OBJ_DIR": "/tmp/build"},
        ... )
        # Executes: make -j8 release OBJ_DIR=/tmp/build
    """
    platform = ctx.platform

    nb_active_cpus = platform.nb_active_cpus()
    parallel_make_lst = ["-j", f"{nb_active_cpus}"] if nb_active_cpus > 1 else []

    argv = [
        "make",
        *parallel_make_lst,
        *targets,
        *(f"{k}={v}" for k, v in options.items()),
    ]

    ctx.exec(argv=argv, cwd=src_dir, output_is_log=True)


def build_dir_from_ctx(ctx: BuildContext) -> Path:
    """
    Generate a platform-specific build directory path.

    Creates a build directory name that includes the platform hostname to allow
    multiple platforms to build from the same source directory without conflicts.

    Args:
        ctx: BuildContext containing fetch results and platform information.

    Returns:
        Path to the platform-specific build directory (not created, just the path).

    Example:
        >>> build_dir = build_dir_from_ctx(ctx)
        >>> print(build_dir)
        /tmp/src/project/build-hostname123
    """
    return ctx.fetch_result.src_dir / f"build-{ctx.platform.hostname}"
