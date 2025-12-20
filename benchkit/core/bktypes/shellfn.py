# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Shell function protocol for platform abstraction.

This module defines the ShellFn protocol, which represents the platform-specific
interface for executing shell commands. Implementations handle the details of
local vs remote execution, SSH connections, and platform-specific command syntax.

Benchmark authors typically don't interact with ShellFn directly - they use the
higher-level ExecFn protocol instead. ShellFn is primarily used internally by
the framework to abstract platform differences.
"""

from pathlib import Path
from typing import Iterable, Protocol

from benchkit.core.bktypes import Argv, Env


class ShellFn(Protocol):
    """
    Protocol for platform-specific shell command execution.

    Implementations of this protocol handle the low-level details of running commands
    on specific platforms (local, remote via SSH, containers, etc.).

    This is an internal protocol - benchmark authors should use ExecFn instead.
    """

    def __call__(
        self,
        command: Argv,
        current_dir: Path | None = None,
        environment: Env | None = None,
        timeout: int | None = None,
        print_output: bool = True,
        output_is_log: bool = False,
        ignore_ret_codes: Iterable[int] = (),
        ignore_any_error_code: bool = False,
    ) -> str:
        """
        Execute a shell command on the platform.

        Args:
            command: Command to execute (list of args or shell string).
            current_dir: Working directory for execution.
            environment: Environment variables (None = inherit).
            timeout: Timeout in seconds (None = no timeout).
            print_output: Whether to print output to console.
            output_is_log: Whether to treat output as log messages.
            ignore_ret_codes: Return codes to treat as success.
            ignore_any_error_code: If True, don't raise on non-zero exit.

        Returns:
            Standard output from the command as a string.

        Raises:
            Platform-specific exceptions for execution failures.
        """
        ...
