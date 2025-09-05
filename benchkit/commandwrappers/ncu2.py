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
import ncu_report
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
import pandas as pd
from io import StringIO


"""
SETTING UP NCU
1) Add ncu_report to PYTHONPATH (/opt/nvidia/nsight-compute/20xy.z.w/extras/python)
   i.e. export PYTHONPATH="${PYTHONPATH}:/opt/nvidia/nsight-compute/2022.4.1/extras/python"

2) Setup NCU sudoless - https://developer.nvidia.com/nvidia-development-tools-solutions-err_nvgpuctrperm-permission-issue-performance-counters
"""

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




"""
report_file_name - name of the generated report file ncu
report_or_log - if False generate an ncu report file (.ncu-rep) otherwise generate a log file
csv - store log file data in csv format if True
config_path - get parameters names from a seperate file instead of passing them as a function

Consult the NCU docks for all the command line options:
https://docs.nvidia.com/nsight-compute/NsightComputeCli/index.html#command-line-options

target_process_filter - only accepts strings denoting regular expressions TODO expand to lists of names
target_kernels - only accepts strings denoting regular expressions TODO expand to lists of names
section - only accepts strings denoting regular expressions
remove_absent_sections/metrics - If the specified section/metric is not correct just remove it and run ncu with sections/meteics that are correct
"""
class NcuWrap(CommandWrapper):

    def __init__(
        self,
        report_file_name: PathType = "ncu_out",
        report_or_log: bool = False,
        ncu_path: Optional[PathType] = None,
        config_path: Optional[PathType] = None,
        force_overwrite: bool = False,
        enable_nvtx: bool = False,
        app_only: bool = False,
        target_processes_filter: Optional[str] = None,
        exclude_process: Optional[str] = None,
        target_kernels: Optional[str] = None,
        launch_count: int = 1,
        user_set: Optional[NcuSet] = None,
        sections: Optional[List[Section]] = None,
        remove_absent_sections: bool = True,
        metrics: Optional[List[Metric]] = None,
        remove_absent_metrics: bool = True,
        user_args: List[str] = None,
        csv: bool = False):

        self._report_or_log = report_or_log
        self._config_path = config_path
        self._report_file_name = report_file_name
        self._force_overwrite = force_overwrite
        self._enable_nvtx = enable_nvtx
        self._app_only = app_only
        self._target_process_filter = target_processes_filter
        self._exclude_process = exclude_process
        self._target_kernels = target_kernels
        self._launch_count = launch_count
        self._user_args = user_args
        self._csv = csv

        self._ncu_bin = _find_ncu_bin(ncu_path)

        self._set = user_set
        if self._set is not None:
            self._validate_set(
                ncu_bin=self._ncu_bin,
                user_set=self._set)

        self._metrics = metrics
        if self._metrics is not None:
            self._validate_metrics(
                ncu_bin=self._ncu_bin,
                metrics=metrics,
                remove_absent_metric=remove_absent_metrics)

        self._sections = sections
        if self._sections is not None:
            self._validate_sections(
                ncu_bin=self._ncu_bin,
                sections=self._sections,
                remove_absent_section=remove_absent_sections)

        super().__init__()

    # TODO only for Ubuntu - expand to check for other OS
    # https://docs.nvidia.com/cuda/cuda-installation-guide-linux/#common-installation-instructions-for-ubuntu
    def dependencies(self):
        return super().dependencies() + [
            # PackageDependency("cuda-toolkit"),
            # PackageDependency("nvidia-gds")
        ]

    def command_prefix(
        self,
        record_data_dir: Optional[PathType],
        **kwargs
    ) -> List[str]:

        cmd_prefix = super().command_prefix(**kwargs)
        options = []

        if self._report_file_name == None:
            raise ValueError(
                "Report data file cannot be None, it is required to save strace output."
            )

        if self._config_path is not None:
            options.append(["--config-file-path", f"{self._config_path}"]) 
        else:
            if self._force_overwrite:
                options.append("-f")

            if self._csv:
                options.append("--csv")

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

            if self._set is not None:
                options.extend(["--set",f"{self._set}"])

            if self._sections is not None:
                for section in self._sections:
                    options.extend(["--section", f"{section}"])

            if self._metrics is not None:
                metrics = _get_metrics_from_list(self._metrics)
                options.extend(["--metrics", f"{metrics}"])

            if self._sections is not None:
                options.extend(["--section", f"regex:{self._sections}"])

            if self._user_args is not None:
                options.extend(self._user_args)

        if record_data_dir is None: record_data_dir = ''
        ncu_report_file_path = os.path.join(record_data_dir, self._report_file_name)
        option = "-o"

        if self._report_or_log:
            option = "--log-file"
            ncu_report_file_path = ncu_report_file_path + ".csv"

        cmd_prefix = (
            ["ncu"]
            + options
            + [
                option,
                f"{ncu_report_file_path}"
            ] 
            + cmd_prefix
        )      

        return cmd_prefix

    
    # method for returing a dictionary from a loaded profile context
    # https://docs.nvidia.com/nsight-compute/PythonReportInterface/index.html
    def _process_ncu_context(
        self,
        profile_context
    ) -> RecordResult:

        # "https://pythonhow.com/how/check-if-a-string-is-a-float/"
        def is_float(word):
            try:
                float(word)
                return True
            except ValueError:
                return False

        metric_dict = {}
        for rnge_idx in range(len(profile_context)):
            rnge = profile_context[rnge_idx]
            for action_idx in range(len(rnge)):
                action = rnge[action_idx]
                # output_dict[f"ncu/range_{rnge_idx}"][f"{str(action)}_{action_idx}"] = {}
                for metric in (action):
                    # handling of string parameters needs to be discussed - better to analyse ncu report file instead
                    try:
                        val = float(action[metric].value())
                        if metric not in metric_dict:
                            metric_dict[f"{rnge_idx}_{metric}"] = val
                        else:
                            metric_dict[f"{rnge_idx}_{metric}"] += val
                    except (ValueError, TypeError):
                        continue

            num_actions = len(rnge)
            for key in metric_dict:
                sum = metric_dict[key]
                mean = sum / num_actions
                metric_dict[key] = mean

        return metric_dict


    def _process_log_file(self, file_path: str) -> RecordResult:
        # read the file contents and remove any lines that start with "=="
        try:
            fp = open(file_path, "r")
            lines = fp.readlines()
            content = ""
            for line in lines:
                if line.startswith("=="):
                    continue

                content += line

            # turn the filtered content into a pandas dataframe
            content_io = StringIO(content)
            try:
                df = pd.read_csv(content_io)

                names = df['Metric Name'].to_list()
                units = df['Metric Unit'].to_list()
                values = df['Metric Value'].to_list()

                output_dict = {}
                for i in range(len(names)):
                    name = str(names[i]) + str(units[i])
                    output_dict[name] = values[i]

                return output_dict
            except (pd.errors.EmptyDataError, pd.errors.DataError, pd.errors.AbstractMethodError):
                return {}

        except FileNotFoundError:
            return {}


    def post_run_hook_update_results(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ):
        assert experiment_results_lines
        assert write_record_file_fun

        # read the report file with the Python package
        # iterate over the ranges
        # for each action in a given range specify the metric and the metric value and add it to the dict

        ncu_out_file_path = os.path.join(record_data_dir, f"{self._report_file_name}")
        output_dict = {}
        if not self._report_or_log: # we saved a report file and not a csv log
            ncu_out_file_path = ncu_out_file_path + ".ncu-rep"

            try:
                profile_context = ncu_report.load_report(ncu_out_file_path)
            except FileNotFoundError:
                return {}

            output_dict = self._process_ncu_context(profile_context)
            return output_dict
        else:
            ncu_out_file_path = ncu_out_file_path + ".csv"
            output_dict = self._process_log_file(ncu_out_file_path)

        return output_dict


    def _get_all_metrics(self, raw_output):

        lines = raw_output.splitlines()
        # first 4 rows and last 2 rows are junk
        useful_lines = lines[4:-2]

        names = []
        for line in useful_lines:
            sline = line.strip()
            vals = sline.split()
            metric_name = vals[0]
            names.append(metric_name)

        return names


    def _get_all_sets(self, raw_output):

        lines = raw_output.splitlines()
        useful_lines = lines[3:]
        names = []
        for line in useful_lines:
            if (not line[0].isalnum()): continue
            sline = line.strip()
            vals = sline.split()
            set_name = vals[0]
            names.append(set_name)

        return names


    def _get_all_sections(self, raw_output):

        lines = raw_output.splitlines()
        useful_lines = lines[3:]
        names = []
        for line in useful_lines:
            sline = line.strip()
            vals = sline.split()
            section_name = vals[0]
            names.append(section_name)

        return names


    def _get_available_options(
            self,
            ncu_bin: PathType,
            cmd_suffix: str):

        raw_output = shell_out(
            command=f"{ncu_bin} {cmd_suffix}",
            print_input=False,
            print_output=False,
        )

        if "metrics" in cmd_suffix:
            return self._get_all_metrics(raw_output)
        elif "sets" in cmd_suffix:
            return self._get_all_sets(raw_output)
        elif "sections" in cmd_suffix:
            return self._get_all_sections(raw_output)
        else:
            raise ValueError(
                                f"The provided command line suffix is not supported: {cmd_suffix}"
                            )


    def _validate_options(
        self,
        ncu_bin: PathType,
        cmd_suffix: str,
        options: List[str],
        remove_absent_options: bool
    ) -> List[str]:
        
        all_options = self._get_available_options(ncu_bin, cmd_suffix)
            
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
            if len(available_options) == 0:
                raise ValueError(
                    f"The options you provided simply do not exist... Options: {', '.join(options)}"
                )

        return list(available_options)


    def _validate_metrics(
        self,
        ncu_bin: PathType,
        metrics: List[Metric],
        remove_absent_metric: bool
    ) -> List[Metric]:

        self._validate_options(ncu_bin, "--query-metrics", metrics, remove_absent_metric)

    def _validate_sections(
        self,
        ncu_bin: PathType,
        sections: List[Section],
        remove_absent_section: bool
    ) -> List[Metric]:

        self._validate_options(ncu_bin, "--list-sections", sections, remove_absent_section)

    def _validate_set(
        self,
        ncu_bin: PathType,
        user_set: NcuSet
    ) -> NcuSet:
        
        all_sets = self._validate_options(ncu_bin, "--list-sets", [user_set], False)




    #https://docs.nvidia.com/cuda/cuda-installation-guide-linux/#post-installation-actions
    # assumes you have a 64 bit OS
    #   def updated_environment(self, environment: Environment) -> Environment:
    #       add_env_vars = {
    #           "PATH": "/usr/local/cuda-12.8/bin/bin${PATH:+:${PATH}}",
    #           "LD_LIBRARY_PATH": "/usr/local/cuda-12.8/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
    #       }
    #       return environment | add_env_vars

    # def wrap(self, command, environment, **kwargs):
    #     return super().wrap(command, environment, **kwargs)