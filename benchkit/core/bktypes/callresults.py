# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Result types for benchmark execution phases.

This module defines the result objects returned by each phase of benchmark execution:
- FetchResult: Captures source code location from the fetch phase
- BuildResult: Captures build artifacts and metadata from the build phase
- RunResult: Captures execution outputs from the run phase

All result types are immutable (frozen=True) to ensure integrity across pipeline stages.
"""

from dataclasses import dataclass, field
from pathlib import Path

from benchkit.core.bktypes import Vars
from benchkit.core.bktypes.execfn import ExecOutput


@dataclass(frozen=True)
class FetchResult:
    """
    Result of the fetch phase.

    Contains the location of fetched source code and any associated metadata.

    Attributes:
        src_dir: Path to the directory containing the fetched source code.
    """

    src_dir: Path


@dataclass(frozen=True)
class BuildResult:
    """
    Result of the build phase.

    Contains build artifacts, paths to binaries, and any build-specific metadata.

    Attributes:
        build_dir: Path to the build directory containing compiled artifacts.
        other: Additional metadata from the build process (e.g., paths to specific binaries,
               temporary directories, or build configuration).
    """

    build_dir: Path
    other: Vars = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    """
    Result of the run phase.

    Contains command execution outputs and any runtime artifacts.
    Designed to be flexible: benchmarks may parse stdout, read output files, or both.

    Attributes:
        outputs: List of ExecOutput objects from commands executed during the run phase.
                 Each ExecOutput captures stdout, stderr, return code, and timing information.
    """

    outputs: list[ExecOutput]
