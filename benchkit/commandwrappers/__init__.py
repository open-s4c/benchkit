# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Wrapper of benchmark commands. Typically used to preprend something to the command of the benchmark
without knowing what the benchmark will be doing.

For example: the initial command of the benchmark is:
  ./do_benchmark

A wrapper "mywrapper" will prepend to the command as follow:
  mywrapper ./do_benchmark

This allows to execute Unix-style utilities that take a command as input, like perf, taskset,
numactl, etc.
"""

from typing import List, Tuple

from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.types import Environment, EnvironmentVariables, SplitCommand


class CommandWrapper:
    """Base class for command wrappers."""

    def __init__(self) -> None:
        pass

    def dependencies(self) -> List[PackageDependency]:
        """Dependencies of the command wrapper.

        Returns:
            List[PackageDependency]: list of dependencies.
        """
        return []

    def command_prefix(self, **_kwargs) -> List[str]:
        """Define the prefix to the command to "wrap".

        Returns:
            List[str]: return a command list on the form of a command formatted like a SplitCommand.
        """
        return []

    def updated_environment(self, environment: Environment) -> Environment:
        """Define a new environment based on the given environment and the new key-values to add to
        the environment for this wrapper.

        Args:
            environment (Environment): the environment to wrap.

        Returns:
            Environment: the new environment with updated keys and values.
        """
        return environment

    def wrap(
        self,
        command: SplitCommand,
        environment: Environment,
        **kwargs,
    ) -> Tuple[SplitCommand, EnvironmentVariables]:
        """Wrap the given command with current command wrapper, optionnally taking information from
        the environment of the command to wrap or "wrapping" it as well.
        Notice that a wrapped command becomes a normal command and can be wrapped again several
        times.

        Args:
            command (SplitCommand): command to wrap.
            environment (Environment): environment of the command, wrappable as well.

        Returns:
            Tuple[SplitCommand, EnvironmentVariables]: the wrapped command and its wrapped
                                                       environment.
        """
        wrapped_command = self.command_prefix(**kwargs) + list(command)
        wrapped_environment = environment if environment is not None else {}
        wrapped_environment = self.updated_environment(environment=wrapped_environment)

        return wrapped_command, wrapped_environment
