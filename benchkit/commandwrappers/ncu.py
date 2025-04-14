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

def get_metrics_from_list(metrics: Optional[List]) -> str:
    return ','.join(metrics)

"""
target_process_filter - only accepts strings denoting regular expressions TODO expand to lists of names
target_kernels - only accepts strings denoting regular expressions TODO expand to lists of names
section - only accepts strings denoting regular expressions

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
        launch_count: int = 1,
        set: Optional[str] = "basic",
        metrics: Optional[List] = None,
        section: Optional[str] = None):

        self._config_path = config_path
        self._report_path = report_path
        self._force_overwrite = force_overwrite
        self._enable_nvtx = enable_nvtx
        self._app_only = app_only
        self._target_process_filter = target_processes_filter
        self._exclude_process = exclude_process
        self._target_kernels = target_kernels
        self._launch_count = launch_count
        self._set = set
        self._metrics = metrics
        self._section = section

        super().__init__()

    # TODO only for Ubuntu - expand to check for other OS
    # https://docs.nvidia.com/cuda/cuda-installation-guide-linux/#common-installation-instructions-for-ubuntu
    def dependencies(self):
        return super().dependencies() + [
            PackageDependency("cuda-toolkit"),
            PackageDependency("nvidia-gds")
        ]

    def command_prefix(self, **kwargs) -> List[str]:
        cmd_prefix = super().command_prefix(**kwargs)
        options = []

        if self._report_path == None:
            raise ValueError(
                "Report data file cannot be None, it is required to save strace output."
            )

        if self._config_path is not None:
            options.append(["--config-file-path", f"{self._config_path}"]) 
        else:
            if self._force_overwrite:
                options.append("-f")

            if self._enable_nvtx:
                options.append("--nvtx")

            if self._app_only:
                options.extend(["--target-processes"],["application-only"])

            # if self._target_process_filter is not None:
            #     options.extend(["--target_process_filter"],[f"regex:{self._target_process_filter}"])

            # if self._exclude_process is not None:
            #     options.extend(["--target_process_filter"],[f"exclude:{self._exclude_process}"])

            if self._target_kernels is not None:
                options.extend(["--kernel-name",f"regex:{self._target_kernels}"])

            options.extend(["--set",f"{self._set}"])

            if self._metrics is not None:
                metrics = get_metrics_from_list(self._metrics)
                options.extend(["--metrics"],[f"{metrics}"])

            if self._section is not None:
                options.extend(["--section"],[f"regex:{self._section}"])

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

    #https://docs.nvidia.com/cuda/cuda-installation-guide-linux/#post-installation-actions
    def updated_environment(self, environment: Environment) -> Environment:
        add_env_vars = {
            "PATH": "/usr/local/cuda-12.8/bin/bin${PATH:+:${PATH}}",
            "LD_LIBRARY_PATH": "/usr/local/cuda-12.8/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
        }
        return environment | add_env_vars

    # def wrap(self, command, environment, **kwargs):
    #     return super().wrap(command, environment, **kwargs)