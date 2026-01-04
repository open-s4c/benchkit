# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Common build utilities for benchmark implementations.

This module provides reusable helper functions for typical benchmark build operations:
- make: Execute make with automatic parallelization
- build_dir_from_ctx: Generate platform-specific build directory paths

These utilities reduce code duplication across benchmark implementations and provide
sensible defaults (e.g., parallel make based on CPU count).
"""

from pathlib import Path
from typing import Iterable, Optional

from benchkit.core.bktypes.contexts import BaseContext, BuildContext


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


def cmake_build(
    ctx: BaseContext,
    build_dir: Path,
    src_dir: Optional[Path] = None,
    build_type: str = "Release",
    target: Optional[str] = None,
):
    """
    Configure (if needed) and build a CMake project.

    - If build_dir/CMakeCache.txt is missing, runs:
        cmake -S <src_dir> -B <build_dir> -DCMAKE_BUILD_TYPE=<build_type>
      (requires src_dir)
    - Then builds:
        cmake --build <build_dir> -j <N> [--target <target>]
    """
    platform = ctx.platform
    build_dir = Path(build_dir)

    nb_active_cpus = platform.nb_active_cpus()
    parallel_lst = ["-j", f"{nb_active_cpus}"] if nb_active_cpus > 1 else []

    cmake_cache = build_dir / "CMakeCache.txt"
    if not platform.comm.isfile(cmake_cache):
        if src_dir is None:
            raise ValueError(
                f"cmake_build: {cmake_cache} missing and src_dir not provided "
                f"(need src_dir to configure)."
            )

        platform.comm.makedirs(path=build_dir, exist_ok=True)

        ctx.exec(
            argv=[
                "cmake",
                "-S",
                str(src_dir),
                "-B",
                str(build_dir),
                f"-DCMAKE_BUILD_TYPE={build_type}",
            ],
            cwd=build_dir,
            output_is_log=True,
        )

    argv = ["cmake", "--build", str(build_dir), *parallel_lst]
    if target is not None:
        argv += ["--target", target]

    ctx.exec(argv=argv, cwd=build_dir, output_is_log=True)


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
