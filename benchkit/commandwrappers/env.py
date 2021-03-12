# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `env` utility, that set environment variables for the wrapped command.
"""

from typing import List, Tuple

from benchkit.platforms import get_current_platform
from benchkit.sharedlibs import EnvironmentVariables
from benchkit.utils.types import Environment, SplitCommand

from . import CommandWrapper, PackageDependency


class EnvWrap(CommandWrapper):
    """
    Command wrapper for the `env` utility, that set environment variables for the wrapped command.
    """

    def __init__(self) -> None:
        super().__init__()
        self.platform = get_current_platform()

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + []

    def wrap(
        self,
        command: SplitCommand,
        environment: Environment,
        **kwargs,
    ) -> Tuple[SplitCommand, EnvironmentVariables]:
        wrapped_command, wrapped_environment = super().wrap(
            command=command,
            environment=environment,
            **kwargs,
        )

        # we need the environment to determine the cmd_prefix
        # hence, we do not redefine the method `command_prefix`
        cmd_prefix = ["env"] + [
            f"{var_name}={var_value}" for var_name, var_value in wrapped_environment.items()
        ]

        wrapped_command = cmd_prefix + wrapped_command
        wrapped_environment = {}

        return wrapped_command, wrapped_environment
