# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Common fetch utilities for benchmark implementations.

This module provides reusable helper functions for typical benchmark fetch operations:
- git_clone: Clone Git repositories with commit checkout
- curl : Download files or fetch remote resources over HTTP(S), FTP, and related protocols
- sed : Apply in-place text substitutions/patches to files

These utilities reduce code duplication across benchmark implementations and provide
sensible defaults (e.g., git clone).
"""
from collections.abc import Iterable
from pathlib import Path

from benchkit.core.bktypes.contexts import BaseContext


def git_clone(
    ctx: BaseContext,
    url: str,
    commit: str,
    parent_dir: Path,
    patches: Iterable[Path] = (),
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
        patches: Apply all the provided patches (default: ()).

    Returns:
        Path to the cloned repository directory.

    Example:
        >>> src_dir = git_clone(
        ...     ctx=fetch_ctx,
        ...     url="https://github.com/facebook/rocksdb.git",
        ...     commit="v10.7.5",
        ...     parent_dir=Path("/tmp/src"),
        ...     patches=[Path("/patches/rocksdb.patch")],
        ... )
    """
    platform = ctx.platform
    comm = platform.comm
    name = url.split("/")[-1].split(".")[0]
    dest = parent_dir / name

    exists = comm.isdir(dest)

    if not exists:
        if not comm.isdir(parent_dir):
            comm.makedirs(path=parent_dir, exist_ok=True)
        ctx.exec(argv=["git", "clone", f"{url}", f"{dest}"], cwd=parent_dir)

    if commit:
        ctx.exec(argv=["git", "checkout", f"{commit}"], cwd=dest)

    if not exists:
        for patch in patches:
            # TODO: This currently assumes patch files are present on the target machine.
            # Check that the patch exists on the target machine
            if not comm.isfile(patch):
                raise FileNotFoundError(
                    f"Patch file not found on target machine: {patch}. "
                    "Applying patches currently assumes patches are available "
                    "locally on the target comm."
                )

            ctx.exec(
                argv=["git", "apply", f"{patch}"],
                cwd=dest,
            )

    return dest


def curl(
    ctx: BaseContext,
    url: str,
    parent_dir: Path,
    name: str,
) -> Path:
    """
    Download a remote file using curl.

    Retrieves a file from the given URL and stores it under the specified
    parent directory with the provided name. If the destination file already
    exists, the download is skipped.

    Args:
        ctx: Context providing platform and execution capabilities.
        url: URL of the file to download (e.g., "https://example.com/file.tar.gz").
        parent_dir: Parent directory where the file will be stored.
        name: Name of the downloaded file.

    Returns:
        Path to the downloaded file.

    Example:
        >>> file_path = curl(
        ...     ctx=fetch_ctx,
        ...     url="https://www.volano.com/files/volano_benchmark_2_9_0.class",
        ...     parent_dir=Path("/tmp/benchmarks"),
        ...     name="volano_benchmark_2_9_0.class",
        ... )
    """
    platform = ctx.platform
    comm = platform.comm
    dest = parent_dir / name

    exists = comm.isfile(dest)

    if not exists:
        if not comm.isdir(parent_dir):
            comm.makedirs(path=parent_dir, exist_ok=True)
        ctx.exec(argv=["curl", "-o", f"{dest}", f"{url}"], cwd=parent_dir)

    return dest


def sed_edit(
    ctx: BaseContext,
    base_dir: Path,
    edits: Iterable[tuple[str, Path]],
) -> None:
    """
    Apply in-place sed edits to files on the target machine.

    Each edit is applied using `sed -i` without invoking a shell. All target
    files must already exist on the target machine.

    Args:
        ctx: Context providing platform and execution capabilities.
        base_dir: Base directory relative to which target file paths are resolved.
        edits: Iterable of (sed_expression, relative_file_path) pairs.

    Raises:
        FileNotFoundError: If any target file does not exist on the target machine.

    Example:
        >>> sed_edit(
        ...     ctx=fetch_ctx,
        ...     base_dir=volano_dir,
        ...     edits=[
        ...         ("s/host=[^ ]*/host=localhost/", Path("startup.sh")),
        ...         ("/# Quit if we cannot find the Java executable file./i java=$(which java)",
        ...             Path("startup.sh")),
        ...     ],
        ... )
    """
    platform = ctx.platform
    comm = platform.comm

    for expr, relpath in edits:
        target = base_dir / relpath

        if not comm.isfile(target):
            raise FileNotFoundError(f"sed target file not found on target machine: {target}")

        ctx.exec(
            argv=["sed", "-i", expr, str(relpath)],
            cwd=base_dir,
        )
