# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Execution function protocol and adapters for running commands.

This module defines:
- ExecOutput: Dataclass capturing the result of command execution
- ExecFn: Protocol defining the execution interface used by benchmarks
- shell2exec: Adapter converting platform shell functions to ExecFn protocol

The ExecFn protocol provides a clean, synchronous API for benchmark authors while
allowing the framework to handle platform-specific details internally.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from benchkit.core.bktypes import Argv, Env
from benchkit.core.bktypes.shellfn import ShellFn
from benchkit.utils.misc import TimeMeasure


@dataclass(frozen=True)
class ExecOutput:
    """
    Result of executing a single command.

    Captures all information about a command execution including outputs, timing,
    and exit status.

    Attributes:
        argv: The command and arguments that were executed.
        cwd: Working directory where the command was executed (None = current directory).
        env: Environment variables used (None = inherited environment).
        stdout: Standard output captured from the command.
        stderr: Standard error captured from the command.
        returncode: Exit code returned by the command (0 = success).
        duration_s: Elapsed execution time in seconds (None if not measured).
        stdout_path: Path where stdout was written (None if not saved to file).
        stderr_path: Path where stderr was written (None if not saved to file).
    """

    argv: Sequence[str]
    cwd: Path | None
    env: Env | None
    stdout: str
    stderr: str
    returncode: int
    duration_s: float | None = None
    stdout_path: Path | None = None
    stderr_path: Path | None = None


class ExecFn(Protocol):
    """
    Protocol defining the synchronous execution interface for benchmarks.

    Provides a clean, keyword-only API for running commands. Implementation details
    (local vs remote execution, output capturing) are hidden from benchmark authors.

    Note: While the API is synchronous, implementations may spawn processes internally
    for parallelism or attachment management.
    """

    def __call__(
        self,
        *,
        argv: Argv,
        cwd: Path | None = None,
        env: Env | None = None,
        timeout_s: int | None = None,
        record_dir: Path | None = None,
        print_output: bool = False,
        output_is_log: bool = False,
        ignore_ret_codes: tuple[int, ...] = (),
        ignore_any_error_code: bool = False,
    ) -> ExecOutput:
        """
        Execute a command and return its output.

        Args:
            argv: Command and arguments (list of strings or single shell string).
            cwd: Working directory for command execution.
            env: Environment variables (None = inherit current environment).
            timeout_s: Maximum execution time in seconds (None = no timeout).
            record_dir: Directory to save output files (None = don't save).
            print_output: Whether to print output to console in real-time.
            output_is_log: Whether to treat output as log messages.
            ignore_ret_codes: Tuple of return codes to treat as success.
            ignore_any_error_code: If True, treat all return codes as success.

        Returns:
            ExecOutput containing command results and metadata.

        Raises:
            Various exceptions depending on implementation (timeout, command not found, etc.).
        """
        ...


def shell2exec(shell_fun: ShellFn) -> ExecFn:
    """
    Convert a platform shell function to the ExecFn protocol.

    Creates an adapter that wraps a platform-specific shell function, adding timing
    measurement and transforming the result into an ExecOutput object.

    Args:
        shell_fun: Platform-specific shell execution function to wrap.

    Returns:
        An ExecFn that delegates to the shell function while providing the
        standard execution interface.

    Example:
        >>> from benchkit.platforms import get_current_platform
        >>> platform = get_current_platform()
        >>> exec_fn = shell2exec(platform.comm.shell)
        >>> result = exec_fn(argv=["echo", "hello"])
        >>> print(result.stdout)
        hello
    """

    def exec_fun(
        argv: Argv,
        cwd: Path | None = None,
        env: Env | None = None,
        timeout_s: int | None = None,
        record_dir: Path | None = None,
        print_output: bool = False,
        output_is_log: bool = False,
        ignore_ret_codes: tuple[int, ...] = (),
        ignore_any_error_code: bool = False,
    ) -> ExecOutput:
        with TimeMeasure() as tm:
            out = shell_fun(
                command=argv,
                current_dir=cwd,
                environment=env,
                timeout=timeout_s,
                print_output=print_output,
                output_is_log=output_is_log,
                ignore_ret_codes=ignore_ret_codes,
                ignore_any_error_code=ignore_any_error_code,
            )
        result = ExecOutput(
            argv=argv,
            cwd=cwd,
            env=env,
            stdout=out,
            stderr="",
            returncode=0,
            duration_s=tm.duration_seconds,
        )
        return result

    return exec_fun
