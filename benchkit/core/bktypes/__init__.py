# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Core type definitions for the benchkit type system.

This module provides fundamental type aliases used throughout the benchkit framework:

- Vars: Flexible dictionary for storing benchmark-related variables and configuration
- Env: Read-only mapping representing environment variables
- Argv: Command-line arguments, either as a sequence of strings or a single shell command string
- RecordResult: Results from benchmark collection, one record per run
"""

from typing import Any, Dict, Mapping, Sequence

Vars = Dict[str, Any]
"""Dictionary storing arbitrary benchmark variables and configuration."""

Env = Mapping[str, str]
"""Read-only mapping of environment variable names to values."""

Argv = Sequence[str] | str
"""Command-line arguments: either a list of argument strings or a single shell command string."""

RecordResult = Vars
"""Benchmark collection result: the single measurement record of a run (one run, one record;
per-line data such as time series belongs in files inside the record directory)."""
