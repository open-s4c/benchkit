# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `nice` utility.

This wrapper prepends the Unix `nice` command to a benchmarked command in
order to adjust its scheduling priority (niceness value). A higher niceness
value lowers the scheduling priority of the process.

This is useful for controlled experiments where process priority must be
explicitly managed (e.g., interference studies or background workload setup).
"""

from typing import List

from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency


class NiceWrap(CommandWrapper):
    """
    Command wrapper for the `nice` utility.

    This wrapper injects `nice -n <value>` before the actual command
    executed by benchkit.
    """

    def __init__(
        self,
        nice_prefix: str = "",
        nice_value: int = 0,
    ):
        """
        Initialize the Nice wrapper.

        Parameters
        ----------
        nice_prefix : str
            Optional prefix to the `nice` binary (e.g., path or `sudo `).
            Example: "sudo " to elevate privileges before applying niceness.
        nice_value : int
            Niceness value to apply. Range typically:
              -20 (highest priority) to 19 (lowest priority).
            Default is 0.
        """
        super().__init__()

        # Construct the nice executable (optionally prefixed).
        # Example: "sudo nice" if nice_prefix="sudo "
        self._nice = f"{nice_prefix}nice"

        # Store the niceness value that will be passed with -n
        self.nice_value = nice_value

    def dependencies(self) -> List[PackageDependency]:
        """
        Declare runtime dependencies required by this wrapper.

        Returns
        -------
        List[PackageDependency]
            List of required system packages. Adds `nice` to the base
            CommandWrapper dependencies.
        """
        return super().dependencies() + [
            PackageDependency("nice"),
        ]

    def command_prefix(  # pylint: disable=arguments-differ
        self,
        **kwargs,
    ) -> List[str]:
        """
        Build the command prefix for benchkit execution.

        This method prepends:
            nice -n <nice_value>

        to the existing command prefix defined by the parent class.

        Returns
        -------
        List[str]
            The full command prefix including the `nice` invocation.
        """

        # Get any existing prefix defined by the parent wrapper(s)
        cmd_prefix = super().command_prefix(**kwargs)

        # Prepend: nice -n <value>
        cmd_prefix = (
            [self._nice]
            + [
                "-n",
                f"{self.nice_value}",
            ]
            + cmd_prefix
        )

        return cmd_prefix
