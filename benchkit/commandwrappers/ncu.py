"""
Command wrapper for the `ncu (Nvidia Nsight Compute CLI)` tool for profiling applications that run on GPUs 
"""

import csv
import json
import os
import os.path
import pathlib
import re
import subprocess
import sys
import time
from functools import cache
from typing import Callable, Dict, List, Optional, Tuple

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandwrappers import CommandWrapper, PackageDependency
from benchkit.communication import CommunicationLayer
from benchkit.helpers.linux import ps, sysctl
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shell import shell_interactive, shell_out
from benchkit.shell.shellasync import AsyncProcess, SplitCommand
from benchkit.utils.types import Environment, PathType

def list_to_regex(names: List) -> str:
    pass

"""
target_process_filter - only accepts strings denoting regular expressions TODO expand to lists of names
target_kernels - only accepts strings denoting regular expressions TODO expand to lists of names

app_only - target_processes command-line option
"""
class NcuWrap(CommandWrapper):

    def __init__(
        self,
        config_path: Optional[PathType],
        report_path: Optional[PathType],
        force_overwrite: bool = False,
        enable_nvtx: bool = False,
        app_only: bool = False,
        target_processes_filter: Optional[str] = None,
        exclude_process: Optional[str] = None,
        target_kernels: Optional[str] = None,
        launch_count: int = 1):

        self._config_path = config_path
        self._report_path = report_path
        self._force_overwrite = force_overwrite
        self._enable_nvtx = enable_nvtx
        self._app_only = app_only
        self._target_process_filter = target_processes_filter
        self._exclude_process = exclude_process
        self._target_kernels = target_kernels
        self._launch_count = launch_count

        super().__init__()

    def dependencies(self):
        return super().dependencies()

    def command_prefix(self, **kwargs) -> List[str]:
        cmd_prefix = super().command_prefix(**kwargs)
        options = []

        if self._report_path == None:
            raise ValueError(
                "Report data file cannot be None, it is required to save strace output."
            )

        if self._config_path != None:
            options.append(["--config-file-path", f"{self._config_path}"]) 
        else:
            if self._force_overwrite:
                options.append("-f")

            if self._enable_nvtx:
                options.append("--nvtx")

            if self._app_only:
                options.append(["--target-processes"],["application-only"])

            if self._target_process_filter != None:
                options.append(["--target_process_filter"],[f"regex:{self._target_process_filter}"])

            if self._exclude_process != None:
                options.append(["--target_process_filter"],[f"exclude:{self._exclude_process}"])

            if self._target_kernels != None:
                options.append(["--kernel-name",f"regex:{self._target_kernels}"])

            

        cmd_prefix = (
            ["ncu"]
            + options
            + [
                "-o",
                f"{self._report_path}"
            ] 
            + cmd_prefix
        )      

        return cmd_prefix
    
    def updated_environment(self, environment):
        return super().updated_environment(environment)

    def wrap(self, command, environment, **kwargs):
        return super().wrap(command, environment, **kwargs)