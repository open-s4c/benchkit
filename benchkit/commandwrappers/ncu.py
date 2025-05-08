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

Metric = str
NcuSet = str
Section = str


def _list_to_regex(names: List) -> str:
    pass


def _get_metrics_from_list(metrics: Optional[List]) -> str:
    return ','.join(metrics)


def _which(executable: str) -> Optional[PathType]:
    result = None

    try:
        result = shell_out(
            command=f"which {executable}", print_input=False, print_output=False
        ).strip()
    except subprocess.CalledProcessError:
        pass

    return result


def _find_ncu_bin(search_path: Optional[PathType]) -> PathType:

    result = None
    kernel = shell_out(
        "uname -r",
        print_input=False,
        print_output=False,
    ).strip()

    if search_path is not None:
        ncu_path = os.path.realpath(os.path.join(search_path, "ncu"))
        result = shell_out(f"which {ncu_path}").strip()

    if result is None:
        result = _which("ncu")

    if result is None:
        raise ValueError(
            "Impossible to find ncu on the platform. Please install and/or specify search_path."
        )

    return result


def _get_available_sets(
    ncu_bin: PathType
) -> List[NcuSet] :
    return _get_available_options(ncu_bin, False, "--list-sets")

def _get_available_sections(
    ncu_bin: PathType
) -> List[Section]:
    return _get_available_options(ncu_bin, False, "--list-sections")

def _get_available_metrics(
    ncu_bin: PathType,
) -> List[Metric]:
    return _get_available_options(ncu_bin, True, "--query-metrics")


def _get_available_options(
        ncu_bin: PathType,
        is_metrics: bool,
        cmd_suffix: str,
) -> List[str]:

    raw_output = shell_out(
        command=f"{ncu_bin} {cmd_suffix}",
        print_input=False,
        print_output=False,
    )

    ids = []

    iterLines = iter(raw_output.splitlines())
    # skips the first 4 rows which are just useless metadata
    metricsIterLines = iterLines[3:]
    for line in metricsIterLines:
        sline = line.strip()
        vals = sline.split()
        ids.append(vals[0+is_metrics])

    return ids


def _validate_metrics(
    ncu_bin: PathType,
    metrics: List[Metric],
    remove_absent_metric: bool
) -> List[Metric]:

    _validate_options(ncu_bin, metrics, True, remove_absent_metric)

def _validate_sections(
    ncu_bin: PathType,
    sections: List[Section],
    remove_absent_section: bool
) -> List[Metric]:

    _validate_options(ncu_bin, sections, False, remove_absent_section)

def _validate_set(
    ncu_bin: PathType,
    set: NcuSet
) -> NcuSet:
    
    all_sets = _get_available_sets(ncu_bin)
    if set not in all_sets:
        raise ValueError(
            f"Specified set is not available: {set}"
        )

    return set


def _validate_options(
    ncu_bin: PathType,
    options: List[str],
    is_metric: bool,
    remove_absent_options: bool
) -> List[str]:
    
    all_options = []
    if is_metric:
        all_options = _get_available_metrics(ncu_bin)
    else:
        all_options = _get_available_sections(ncu_bin)
        
    set_all_options = set(all_options)
    set_user_options = set(options)

    not_available_options = set_user_options.difference(set_all_options)
    available_options = set_user_options

    if len(not_available_options) != 0:
        if not remove_absent_options:
            raise ValueError(
                f"The following provided metrics are not available: {', '.join(not_available_options)}"
            )
        available_options = set_user_options.difference(not_available_options)

    return List(available_options)


"""
target_process_filter - only accepts strings denoting regular expressions TODO expand to lists of names
target_kernels - only accepts strings denoting regular expressions TODO expand to lists of names
section - only accepts strings denoting regular expressions

app_only - target_processes command-line option
"""
class NcuWrap(CommandWrapper):

    def __init__(
        self,
        report_path: PathType,
        ncu_path: Optional[PathType] = None,
        config_path: Optional[PathType] = None,
        force_overwrite: bool = False,
        enable_nvtx: bool = False,
        app_only: bool = False,
        target_processes_filter: Optional[str] = None,
        exclude_process: Optional[str] = None,
        target_kernels: Optional[str] = None,
        launch_count: int = 1,
        set: Optional[NcuSet] = "basic",
        sections: Optional[List[Section]] = None,
        remove_absent_sections: bool = True,
        metrics: Optional[List[Metric]] = None,
        remove_absent_metrics: bool = True,
        user_args: List[str] = None):

        self._config_path = config_path
        self._report_path = report_path
        self._force_overwrite = force_overwrite
        self._enable_nvtx = enable_nvtx
        self._app_only = app_only
        self._target_process_filter = target_processes_filter
        self._exclude_process = exclude_process
        self._target_kernels = target_kernels
        self._launch_count = launch_count
        self._user_args = user_args

        self._ncu_bin = _find_ncu_bin(ncu_path)

        if set is not None:
            self._set = _validate_set(
                ncu_bin=self._ncu_bin,
                set=set)

        if metrics is not None:
            self._metrics = _validate_metrics(
                        ncu_bin=self._ncu_bin,
                        metrics=metrics,
                        remove_absent_metric=remove_absent_metrics)

        if sections is not None:
            self._sections = _validate_sections(
                        ncu_bin=self._ncu_bin,
                        sections=sections,
                        remove_absent_section=remove_absent_sections)

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

            if self._sections is not None:
                for section in self._sections:
                    options.extend(["--section", f"{section}"])

            if self._metrics is not None:
                metrics = _get_metrics_from_list(self._metrics)
                options.extend(["--metrics", f"{metrics}"])

            if self._section is not None:
                options.extend(["--section", f"regex:{self._section}"])

            if self._user_args is not None:
                options.extend(self._user_args)

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
    # assumes you have a 64 bit OS
    def updated_environment(self, environment: Environment) -> Environment:
        add_env_vars = {
            "PATH": "/usr/local/cuda-12.8/bin/bin${PATH:+:${PATH}}",
            "LD_LIBRARY_PATH": "/usr/local/cuda-12.8/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
        }
        return environment | add_env_vars

    # def wrap(self, command, environment, **kwargs):
    #     return super().wrap(command, environment, **kwargs)