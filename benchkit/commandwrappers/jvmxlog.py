# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `Xlog` functionality of the JVM.
"""

import os
from typing import List, Optional, Tuple

from benchkit.platforms import get_current_platform
from benchkit.sharedlibs import EnvironmentVariables
from benchkit.utils.types import Environment, PathType, SplitCommand

from . import CommandWrapper, PackageDependency


class JVMXlogWrap(CommandWrapper):
    """
Command wrapper for the `Xlog` functionality of the JVM.
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
        record_data_dir: Optional[PathType] = None,
        **kwargs,
    ) -> Tuple[SplitCommand, EnvironmentVariables]:

        if record_data_dir is None:
            raise ValueError("Record data directory cannot be None, it is required to save the JVMXlog data.")
            
        jvmxlog_pathname = os.path.join(record_data_dir, "jvmxlog.log")
        print(f"DEBUGPRINT[29]: jvmxlog.py:37: jvmxlog_pathname={jvmxlog_pathname}")
        cmd_infix = [f'-Xlog:gc*:file="{jvmxlog_pathname}"' ]
        # cmd_suffix = []

        wrapped_command = [command[0]] + cmd_infix + command[1:]
        print(f"DEBUGPRINT[30]: jvmxlog.py:45: wrapped_command={wrapped_command}")
        wrapped_environment = environment

        return wrapped_command, wrapped_environment
