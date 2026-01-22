# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Core type definitions for the benchkit type system.

This module provides fundamental type aliases used throughout the benchkit framework:

- Vars: Flexible dictionary for storing benchmark-related variables and configuration
- Env: Read-only mapping representing environment variables
- Argv: Command-line arguments, either as a sequence of strings or a single shell command string
- RecordResult: Results from benchmark collection, either a single record or list of records
"""

from typing import Any, Dict, Mapping, Sequence

Vars = Dict[str, Any]
"""Dictionary storing arbitrary benchmark variables and configuration."""

Env = Mapping[str, str]
"""Read-only mapping of environment variable names to values."""

Argv = Sequence[str] | str
"""Command-line arguments: either a list of argument strings or a single shell command string."""

RecordResult = Vars | list[Vars]
"""Benchmark collection result: either a single measurement record or list of records."""
