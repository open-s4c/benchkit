# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module of the main benchmark class, parent of all benchkit benchmarks.
"""

import inspect
import itertools
import json
import os
import pathlib
from multiprocessing import Barrier
from subprocess import CalledProcessError
from typing import IO, Any, Dict, Iterable, List, Optional, Protocol, Tuple

from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies import check_dependencies
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import get_current_platform
from benchkit.sharedlibs import SharedLib
from benchkit.sharedlibs.tiltlib import TiltLib
from benchkit.shell.shellasync import AsyncProcess, shell_async
from benchkit.utils.gdb import generate_gdb_script_from_cmd
from benchkit.utils.misc import CSV_SEPARATOR, TimeMeasure, dict_union, seconds2pretty
from benchkit.utils.system import get_boot_args
from benchkit.utils.tee import teeprint
from benchkit.utils.types import (
    Command,
    Constants,
    Environment,
    PathType,
    Pretty,
    SplitCommand,
)
from benchkit.utils.variables import list_groupby

RecordKey = str
RecordValue = Any
RecordParameters = Dict[RecordKey, RecordValue]
RecordResult = Dict[RecordKey, RecordValue]


class WriteRecordFileFunction(Protocol):
    """
    Callback to write a file in the right directory corresponding to the current executing record.
    """

    def __call__(
        self,
        file_content: str,
        filename: PathType,
    ) -> None:
        ...


class PreRunHook(Protocol):
    """
    Callback for running hooks before the execution of a benchmark.
    """

    def __call__(
        self,
        build_variables: RecordResult,
        run_variables: RecordResult,
        record_data_dir: PathType,
    ) -> None:
        ...


class PostRunHook(Protocol):
    """
    Callback for running hooks after the execution of a benchmark.
    """

    def __call__(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> Optional[RecordResult]:
        ...


class CommandAttachment(Protocol):
    """
    Callback for a command that will be attached to the benchmark command (asynchronously).
    """

    def __call__(
        self,
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:
        ...


class Benchmark:
    """
    Represent a single benchmark to be run, exploring the parameter space of the associated
    campaign. Wrappers, attachments, libraries, and hooks can be provided to apply recurring
    standalone processing to the benchmark.
    """

    def __init__(
        self,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
    ) -> None:
        # TODO tilt is still hardcoded for now, remove tilt from the base benchmark class
        tilts = [lib for lib in shared_libs if isinstance(lib, TiltLib)]
        tilt = tilts[0] if tilts else None

        self._command_wrappers = command_wrappers
        self._command_attachments = list(command_attachments)
        self._shared_libs = shared_libs
        self._pre_run_hooks = pre_run_hooks
        self._post_run_hooks = post_run_hooks

        self.tilt = tilt
        self.platform = get_current_platform()

        self._configured = False
        self._experiment_name = None
        self._benchmark_name = None
        self._csv_output_path = None
        self._base_data_dir = None
        self._benchmark_duration_seconds = None
        self._nb_runs = None
        self._variables = None
        self._other_campaigns_seconds = None
        self._use_tilt = None
        self._constants = None
        self._pretty_variables = None

        self._total_nb_runs = None
        self._nb_runs_done = 0
        self._first_line_is_printed = False

        self._debug = False
        self._gdb = False
        self._flamegraph_path: Optional[PathType] = None

    @property
    def bench_src_path(self) -> pathlib.Path:
        """
        Return the path to the source of the benchmark.

        Returns:
            pathlib.Path: the path to the source of the benchmark.
        """
        raise NotImplementedError

    @staticmethod
    def get_build_var_names() -> List[str]:
        """
        Get the names of the build variables.

        Returns:
            List[str]: the names of the build variables.
        """
        raise NotImplementedError

    @staticmethod
    def get_run_var_names() -> List[str]:
        """
        Get the names of the run variables.

        Returns:
            List[str]: the names of the run variables.
        """
        raise NotImplementedError

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        """
        Get the names of the tilt variables.

        Returns:
            List[str]: the names of the tilt variables.
        """
        raise NotImplementedError

    @staticmethod
    def _write_to_record_data_dir(
        file_content: str,
        filename: PathType,
        record_data_dir: Optional[PathType],
    ) -> None:
        if record_data_dir is None:
            return
        rdd = pathlib.Path(record_data_dir)

        output_path = rdd / filename
        with open(output_path, "w") as output_file:
            output_file.write(file_content)

    @staticmethod
    def _log_footers(
        output_file: IO[str],
        total_duration_seconds: float,
    ) -> None:
        def log_line(line: str) -> None:
            print(f"# {line}", file=output_file)
            output_file.flush()

        total_duration_pretty = seconds2pretty(total_duration_seconds)
        log_line(f"total_duration_seconds: {total_duration_seconds}")
        log_line(f"total_duration_pretty: {total_duration_pretty}")

    @staticmethod
    def _log_prebuild_time(
        output_file: IO[str],
        prebuild_seconds: float,
    ) -> None:
        def log_line(line: str) -> None:
            print(f"# {line}", file=output_file)
            output_file.flush()

        prebuild_duration_pretty = seconds2pretty(prebuild_seconds)
        log_line(f"prebuild_duration_seconds: {prebuild_seconds}")
        log_line(f"prebuild_duration_pretty: {prebuild_duration_pretty}")

    @staticmethod
    def _log_total_time_info(
        total_nb_runs: int,
        total_seconds: int,
    ) -> None:
        print(f"[INFO] Total number of runs: {total_nb_runs}")
        print(f"[INFO] Expected duration: {total_seconds}")

    @staticmethod
    def _log_current_time_info(
        total_nb_runs: int,
        nb_runs_done: int,
        bench_duration: int,
        other_campaigns_seconds: int,
    ) -> None:
        time_suffix = ""
        full_time_str = ""
        if bench_duration is not None:
            remaining_seconds = (total_nb_runs - nb_runs_done) * bench_duration
            remaining_time = seconds2pretty(remaining_seconds)
            time_suffix = (
                f", current campaign expected remaining time: "
                f"~{remaining_seconds} seconds, "
                f"i.e. ~{remaining_time}"
            )
            full_remaining_seconds = remaining_seconds + other_campaigns_seconds
            full_remaining_time = seconds2pretty(full_remaining_seconds)
            full_time_str = (
                f"[INFO] Full campaign suite estimated remaining time: "
                f"~{full_remaining_seconds} seconds, "
                f"i.e. ~{full_remaining_time}"
            )

        run_str = f"{nb_runs_done + 1: {len(str(total_nb_runs))}}"
        print(f"[INFO] Run {run_str}/{total_nb_runs}{time_suffix}")
        if full_time_str:
            print(full_time_str)

    def dependencies(self) -> List[PackageDependency]:
        """
        Return required dependencies of the current benchmark.

        Returns:
            List[PackageDependency]: required dependencies of the current benchmark.
        """
        sharedlibs_deps = [shared_lib.dependencies() for shared_lib in self._shared_libs]
        cmdwraps_deps = [
            command_wrapper.dependencies() for command_wrapper in self._command_wrappers
        ]
        all_deps_it = itertools.chain.from_iterable(sharedlibs_deps + cmdwraps_deps)
        all_deps = list(all_deps_it)
        return all_deps

    def check_dependencies(self) -> None:
        """
        Check that dependencies of the current benchmark are present on the target platform.
        """
        if self.platform.comm.is_local:
            check_dependencies(
                all_dependencies=self.dependencies(),
                platform=self.platform,
            )
        else:  # TODO skip remote dependency check for now because of inconsistencies
            pass

    def configure_variables(
        self,
        experiment_name: str,
        benchmark_name: str,
        csv_output_path: PathType,
        base_data_dir: Optional[PathType],
        benchmark_duration_seconds: int,
        nb_runs: int,
        constants: Constants,
        variables: RecordParameters,
        pretty_variables: Pretty,
        debug: bool,
        gdb: bool,
    ) -> None:
        """
        Configure the benchmark variables once they are associated with a campaign.

        Args:
            experiment_name (str):
                name of the experiment.
            benchmark_name (str):
                name of the benchmark.
            csv_output_path (PathType):
                path of the CSV output file.
            base_data_dir (Optional[PathType]):
                path of the base data directory, where to store the data of each record.
                This step is ignored if None is given.
            benchmark_duration_seconds (int):
                duration, in seconds, of a single run of the benchmark (when the benchmark supports
                a fixed duration).
            nb_runs (int):
                number of runs for each fixed configuration (with the same variable values).
            constants (Constants):
                constant columns to add to the results.
            variables (RecordParameters):
                records that map the variable names to the variable values.
            pretty_variables (Pretty):
                pretty translation of variable values.
            debug (bool):
                whether to enable debug.
            gdb (bool):
                whether to enable gdb.

        Raises:
            ValueError: if the benchmark is already configured.
        """
        if self._configured:
            raise ValueError("Benchmark already configured")

        self._configured = True
        self._experiment_name = experiment_name
        self._benchmark_name = benchmark_name
        self._csv_output_path = pathlib.Path(csv_output_path)
        self._base_data_dir = pathlib.Path(base_data_dir) if base_data_dir is not None else None
        self._benchmark_duration_seconds = benchmark_duration_seconds
        self._nb_runs = nb_runs
        self._constants = constants
        self._variables = variables

        self._use_tilt = self.tilt is not None

        self._pretty_variables = pretty_variables

        self._debug = debug
        self._gdb = gdb

    def valid_experiment_parameters(
        self,
        **kwargs,
    ) -> bool:
        """
        Return whether the provided experiment parameters are valid.

        Returns:
            bool: whether the provided experiment parameters are valid.
        """
        self._check_config()

        results = []
        if "core0" in kwargs:
            thread0 = kwargs["core0"]
            result = thread0 < self.platform.nb_cpus()
            results.append(result)
        if "core1" in kwargs:
            thread1 = kwargs["core1"]
            result = thread1 < self.platform.nb_cpus()
            results.append(result)

        return all(results)

    def total_nb_runs(self) -> int:
        """
        Compute the total number of runs of this benchmark once configured.

        Returns:
            int: the total number of runs.
        """
        self._check_config()

        if self._total_nb_runs is None:
            nb_runs = self._nb_runs

            nb_cases = 0

            for record_params in self._variables:
                build_variables, run_variables, _, _ = self._group_record_parameters(
                    record_parameters=record_params,
                )

                experiment_point = {}
                experiment_point.update(build_variables)
                experiment_point.update(run_variables)

                is_valid_point = self.valid_experiment_parameters(**experiment_point)
                if is_valid_point:
                    nb_cases += 1

            result = nb_cases * nb_runs
            self._total_nb_runs = result

        return self._total_nb_runs

    def expected_total_duration_seconds(self) -> int | None:
        """
        Compute the expected total time (in seconds) of this benchmark once configured.
        If benchmark_duration_seconds is not set, it returns None.

        Returns:
            int | None:
                the expected total time (in seconds) of this benchmark once configured.
        """
        self._check_config()

        if self._benchmark_duration_seconds is None:
            return None

        bds = self._benchmark_duration_seconds
        result = self.total_nb_runs() * bds
        return result

    def get_execution_set(
        self,
        continuing: bool,
    ) -> Tuple[List[Dict[str, str]], bool]:
        """
        Return the set of executions.

        Args:
            continuing (bool): whether caching of the results is enabled.

        Returns:
            Tuple[List[Dict[str, str]], bool]:
                the execution set and whether to print comments (in the CSV header).
        """
        if not continuing or not self._csv_output_path.exists():
            return [], True

        with open(self._csv_output_path, "r") as csv_output_file:
            output_executions = [
                line.strip()
                for line in csv_output_file.readlines()
                if not line.strip().startswith("#")
            ]

            if len(output_executions) > 0:
                print_comments = False
                header = output_executions[0]
                records_lines = output_executions[1:]

                keys = header.split(";")
                records = [dict(zip(keys, record_line.split(";"))) for record_line in records_lines]
            else:
                print_comments = True
                records = []

        return records, print_comments

    def filter_result_execution_set(
        self,
        record_params: Dict[str, Any],
        executions_dict: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """
        Remove from executions_dict keys that are not parameters. I.e., remove result keys.

        Args:
            record_params (Dict[str, Any]):
                parameters of the current record.
            executions_dict (List[Dict[str, str]]):
                currently recorded results of executions.

        Returns:
            List[Dict[str, str]]:
                the filtered executions_dict.
        """
        if executions_dict:
            for execution in executions_dict:
                results_keys = execution.keys() - record_params.keys()
                results_keys = results_keys - self._constants.keys()
                results_keys = results_keys - {"experiment_name", "rep"}

                pretty_keys = [k for k in results_keys if k.endswith("_pretty")]
                for pretty_key in pretty_keys:
                    results_keys.remove(pretty_key)

                for key in results_keys:
                    if key in execution:
                        execution.pop(key)

        return executions_dict

    def run(
        self,
        other_campaigns_seconds: int,
        barrier: Optional[Barrier],
        continuing: bool,
    ) -> None:
        """
        Run the benchmark, all executions.

        Args:
            other_campaigns_seconds (int):
                how many seconds remain in other campaigns (that are run sequentially).
            barrier (Optional[Barrier]):
                in case it is necessary to synchronize the start, the associated barrier.
            continuing (bool):
                whether caching of results is enabled.
        """
        self._check_config()

        self._other_campaigns_seconds = other_campaigns_seconds

        self._configure_shared_libs()

        if self._use_tilt:
            self.tilt.clean()
            tilt_gb = list_groupby(
                variables_names=self.get_tilt_var_names(),
                bench_variables=self._variables,
            )
            for tilt_variables, _ in tilt_gb:
                self.build_tilt(**tilt_variables)

        prebuild_seconds = self.prebuild_bench(
            benchmark_duration_seconds=self._benchmark_duration_seconds,
        )

        expected_total_seconds = self.expected_total_duration_seconds()

        self._log_total_time_info(
            total_nb_runs=self.total_nb_runs(),
            total_seconds=expected_total_seconds,
        )

        with TimeMeasure() as run_duration:
            executions_dict, print_comments_header = self.get_execution_set(continuing)

            if print_comments_header:
                with open(self._csv_output_path, "a") as csv_output_file:
                    self._log_headers(
                        output_file=csv_output_file,
                        experiment_name=self._experiment_name,
                        benchmark_duration_seconds=self._benchmark_duration_seconds,
                        nb_runs=self._nb_runs,
                        start_time=run_duration.start_time,
                        expected_duration_seconds=expected_total_seconds,
                    )
                    if prebuild_seconds is not None:
                        self._log_prebuild_time(
                            output_file=csv_output_file,
                            prebuild_seconds=prebuild_seconds,
                        )

            self._nb_runs_done = 0
            self._first_line_is_printed = False

            build_gb = list_groupby(
                variables_names=self.get_build_var_names(),
                bench_variables=self._variables,
            )

            for build_variables, build_run_variables in build_gb:
                example_build_run_variables = build_run_variables[0]
                actual_build_variables = {
                    var_name: var_value
                    for var_name, var_value in build_variables.items()
                    if (
                        var_name in example_build_run_variables
                        and var_value == example_build_run_variables[var_name]
                    )
                }
                valid = self._build_one_bench(actual_build_variables)
                if valid:
                    for record_params in build_run_variables:
                        executions_dict = self.filter_result_execution_set(
                            record_params,
                            executions_dict,
                        )

                        self._run_single_run(
                            record_parameters=record_params,
                            executions_dict=executions_dict,
                            continuing=continuing,
                            barrier=barrier,
                        )

        actual_total_seconds = run_duration.duration_seconds

        with open(self._csv_output_path, "a") as csv_output_file:
            self._log_footers(
                output_file=csv_output_file,
                total_duration_seconds=actual_total_seconds,
            )

        print(f"[INFO] Benchmark done. " f'Results are stored in: "{self._csv_output_path}"')

    def build_tilt(
        self,
        **kwargs,
    ) -> None:
        """
        Build the tilt library related to this benchmark.
        TODO this is deprecated, now benchmark is independent from tilt
        """

    def prebuild_bench(
        self,
        **kwargs,
    ) -> int:
        """
        Do a build step that is independent of the build variables.

        Returns:
            int: time it took, in seconds.
        """
        return 0

    def clean_bench(self) -> None:
        """
        Clean the benchmark from build files.
        """
        pass

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        """
        Build the benchmark, feeding to the function the build variables.
        """
        raise NotImplementedError

    def single_run(
        self,
        **kwargs,
    ) -> str | AsyncProcess:
        """
        Execute a single run of the benchmark, feeding to the function the run variables.
        It returns the output of the benchmark command in the case of synchronous command,
        and the asynchronous process in the case of asynchronous command.

        Returns:
            str | AsyncProcess:
                the output of the benchmark command in the case of synchronous command, and the
                asynchronous process in the case of asynchronous command.
        """
        raise NotImplementedError

    def parse_output_to_results(
        self,
        command_output: str,
        build_variables: Dict[str, Any],
        run_variables: Dict[str, Any],
        benchmark_duration_seconds: int,
        record_data_dir: PathType,
        **kwargs,
    ) -> RecordResult:
        """
        Parse the output of the benchmark commands and convert it into a dictionary of recorded
        results.

        Args:
            command_output (str):
                raw output result of the benchmark command.
            build_variables (Dict[str, Any]):
                build variables and their values.
            run_variables (Dict[str, Any]):
                run variables and their values.
            benchmark_duration_seconds (int):
                duration of a single benchmark run.
            record_data_dir (PathType):
                path to directory where to store the results.

        Returns:
            RecordResult:
                the record results corresponding to the output of the run.
        """
        raise NotImplementedError

    def run_bench_command(
        self,
        run_command: SplitCommand,
        wrapped_run_command: SplitCommand,
        current_dir: PathType,
        environment: Environment,
        wrapped_environment: Environment,
        print_output: bool,
        timeout: int | None = None,
        ignore_ret_codes: Iterable[int] = (),
        ignore_any_error_code: bool = False,
        **kwargs,
    ) -> str | AsyncProcess:
        """
        Run a benchmark command, wrapping everything, possibly attaching debugger, etc.

        Args:
            run_command (SplitCommand):
                initial command to run.
            wrapped_run_command (SplitCommand):
                command wrapped with everything configured in the benchmark.
            current_dir (PathType):
                directory where to run the command.
            environment (Environment):
                initial environment variables to pass to the command.
            wrapped_environment (Environment):
                environment wrapped with everything configured in the benchmark.
            print_output (bool):
                whether to print the output of the benchmark command.
            ignore_ret_codes (Iterable[int], optional):
                List of error code to ignore if it is the return code of the command.
                Defaults to () (empty collection).
            ignore_any_error_code (bool, optional):
                whether to error any error code returned by the command.

        Returns:
            str | AsyncProcess:
                the output of the benchmark command in the case of synchronous command, and the
                asynchronous process in the case of asynchronous command.
        """
        if self._gdb:
            self.debug_session(
                run_command=run_command,
                current_dir=current_dir,
                environment=environment,
            )
            return ""  # unreachable
        if self._command_is_async():
            process = self._run_async_bench_command(
                wrapped_run_command=wrapped_run_command,
                current_dir=current_dir,
                wrapped_environment=wrapped_environment,
                **kwargs,
            )
            return process

        # Synchronous case where the benchmark returns the output string:
        output = self.platform.comm.shell(
            command=wrapped_run_command,
            current_dir=current_dir,
            environment=wrapped_environment,
            print_output=print_output,
            timeout=timeout,
            ignore_ret_codes=ignore_ret_codes,
            ignore_any_error_code=ignore_any_error_code,
        )
        return output

    def must_debug(self) -> bool:
        """
        Return whether the benchmark must be debugged.

        Returns:
            bool: whether the benchmark must be debugged.
        """
        return self._debug

    def debug_session(
        self,
        run_command: SplitCommand,
        current_dir: PathType,
        environment: Environment,
    ) -> None:
        """
        Start a debugging session.

        Args:
            run_command (SplitCommand):
                the command to run and that must be debugged.
            current_dir (PathType):
                the path to the directory where to run the command.
            environment (Environment):
                the environment variables to pass to the command.
        """
        current_dir = pathlib.Path(current_dir)
        gdb_script_path = current_dir / ".gdbinit"
        generate_gdb_script_from_cmd(
            gdb_script_path=gdb_script_path,
            run_command=run_command,
            environment=environment,
        )

        self.platform.comm.shell(
            command="gdb",
            current_dir=current_dir,
            environment=None,
            shell=True,
            output_is_log=True,
        )
        print(
            (
                f"[DEBUG] To reproduce the debug session, "
                f"type the following commands:\n  "
                f"cd {current_dir}\n  gdb"
            )
        )
        raise SystemExit(0)

    def _max_nb_threads(self) -> int:
        # we allow over-subscription
        result = 4 * self.platform.nb_cpus()
        return result

    def _parallel_make_str(self) -> str:
        nb_active_cpus = self.platform.nb_active_cpus()
        parallel_make_str = f" -j {nb_active_cpus} " if nb_active_cpus > 1 else ""
        return parallel_make_str

    def _check_config(self) -> None:
        if not self._configured:
            raise ValueError("Benchmark must be configured before calling a method")

    def _configure_shared_libs(self) -> None:
        for shared_lib in self._shared_libs:
            shared_lib.configure()

    def _preload_env(
        self,
        **kwargs,
    ) -> Environment:
        ld_preloads = []
        other_environment = {}
        for shared_lib in self._shared_libs:
            preloads, other_env = shared_lib.preload(**kwargs)
            ld_preloads.extend(preloads)
            other_environment.update(other_env)

        result_environment = {}
        if ld_preloads:
            result_environment["LD_PRELOAD"] = ":".join(map(str, ld_preloads))
        result_environment.update(other_environment)

        if not result_environment:
            result_environment = None

        return result_environment

    def _wrap_command(
        self,
        run_command: List[str],
        environment: Environment,
        **kwargs,
    ) -> Tuple[Command, Environment]:
        wrapped_command = list(run_command)
        wrapped_environment = environment

        for command_wrapper in self._command_wrappers[::-1]:
            wrapped_command, wrapped_environment = command_wrapper.wrap(
                command=wrapped_command,
                environment=wrapped_environment,
                **kwargs,
            )

        if not wrapped_environment:
            wrapped_environment = None

        return wrapped_command, wrapped_environment

    def _build_one_bench(
        self,
        build_variables: Dict[str, Any],
    ) -> bool:
        """
        Build a single instance of the benchmark using the given build variables.

        Args:
            build_variables (Dict[str, Any]): variables useful at build-time to build the benchmark.

        Returns:
            bool: if the build variables are valid to generate a benchmark.
        """
        if not self.valid_experiment_parameters(**build_variables):
            return False

        self.clean_bench()
        self.build_bench(
            benchmark_duration_seconds=self._benchmark_duration_seconds,
            constants=self._constants,
            **build_variables,
        )
        return True

    def _group_record_parameters(
        self,
        record_parameters: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Partition the record parameters into build/run/tilt/other variable groups.

        Args:
            record_parameters (Dict[str, Any]): parameters to split.

        Returns:
            Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
                split parameters (build/run/tilt/other).
        """
        build_variables = {
            k: record_parameters[k] for k in self.get_build_var_names() if k in record_parameters
        }
        run_variables = {
            k: record_parameters[k] for k in self.get_run_var_names() if k in record_parameters
        }
        tilt_variables = {
            k: record_parameters[k] for k in self.get_tilt_var_names() if k in record_parameters
        } if self._use_tilt else {}
        other_variables = {
            k: record_parameters[k]
            for k in record_parameters
            if k not in build_variables and k not in run_variables
        }
        return build_variables, run_variables, tilt_variables, other_variables

    def _is_result_cached(
        self,
        record_to_run: Dict[str, Any],
        cached_records: Iterable[Dict[str, Any]],
    ) -> bool:
        for cached_record in cached_records:
            same_record = True
            for key in record_to_run:
                if key in cached_record:
                    if cached_record[key] != record_to_run[key]:
                        same_record = False
                        break
            if same_record:
                return True

    def _temp_record_prefix(self) -> pathlib.Path:
        # TODO warning, does not support concurrent execution
        # for this, need a unique record path for each benchmark run
        return pathlib.Path("/tmp/benchkit_record")

    def _temp_record_data_dir(self, record_data_dir: pathlib.Path):
        # The ./ prefix is necessary since pathlib ignores the first
        # argument to the / operator if the second argument is an 
        # absolute path. So we need to ensure the second argument is
        # never an absolute path. 
        return self._temp_record_prefix() / f"./{record_data_dir}"

    def _run_single_run(
        self,
        record_parameters: Dict[str, Any],
        executions_dict: Iterable[Dict[str, str]],
        continuing: bool,
        barrier: Optional[Barrier],
    ) -> None:
        """
        Run `nb_runs` times a single instance of the benchmark using the given record parameters.

        Args:
            record_parameters (Dict[str, Any]):
                input parameters for the current record run.
            executions_dict (Iterable[Dict[str, str]]):
                current information that need to be stored in the record.
            continuing (bool):
                whether caching of the results is enabled.
            barrier (Optional[Barrier]):
                if applicable, the barrier for the benchmark to wait.
        """
        (
            build_variables,
            run_variables,
            _,  # tilt_variables, TODO remove tilt
            other_variables,
        ) = self._group_record_parameters(record_parameters=record_parameters)

        for run_id in range(1, self._nb_runs + 1):
            record_data_dir = self._record_data_dir(
                record_parameters=record_parameters,
                run_id=run_id,
            )

            experiment_results = {
                "experiment_name": self._experiment_name,
                "benchmark_name": self._benchmark_name,
            }
            if self._constants is not None:
                experiment_results.update(self._constants)
            experiment_results.update(build_variables)
            experiment_results.update(run_variables)
            experiment_results.update(other_variables)

            if self._pretty_variables:
                for var_name in self._pretty_variables:
                    ugly2pretty = self._pretty_variables[var_name]
                    ugly_var_value = experiment_results.get(var_name)
                    pretty_var_value = ugly2pretty.get(ugly_var_value, ugly_var_value)
                    experiment_results[f"{var_name}_pretty"] = f'"{pretty_var_value}"'

            experiment_results.update({"rep": run_id})

            if not self.valid_experiment_parameters(**experiment_results):
                break

            self._log_current_time_info(
                total_nb_runs=self.total_nb_runs(),
                nb_runs_done=self._nb_runs_done,
                bench_duration=self._benchmark_duration_seconds,
                other_campaigns_seconds=self._other_campaigns_seconds,
            )

            def str_param(value: List[str] | str) -> str:
                if isinstance(value, list):
                    return f'[{", ".join(map(str, value))}]'
                return str(value)

            execution_parameters = {k: str_param(v) for k, v in experiment_results.items()}

            # If this execution has already been done and continuing option is activated,
            # then skip
            if continuing and self._is_result_cached(execution_parameters, executions_dict):
                print("[CONTINUING] This execution has already been done. Skipping it")
                self._nb_runs_done += 1
                if not self._first_line_is_printed:
                    self._first_line_is_printed = True
                    with open(self._csv_output_path, "a") as csv_output_file:
                        teeprint(content="# Continuing campaign execution", file=csv_output_file)
                continue

            # Replace record_data_dir with a temporary data directory for the 
            # wrapper to write their files to. (Only if the host is remote)
            temp_record_data_dir = record_data_dir
            if not self.platform.comm.is_local:
                temp_record_data_dir = self._temp_record_data_dir(record_data_dir)
                self.platform.comm.makedirs(temp_record_data_dir, True)

            for pre_run_hook in self._pre_run_hooks:
                pre_run_hook(
                    build_variables=build_variables,
                    run_variables=run_variables,
                    record_data_dir=temp_record_data_dir,
                )

            if barrier is not None:
                barrier_ret = barrier.wait()
                if barrier_ret == 0:
                    barrier.reset()

            single_run_return = self.single_run(
                platform=self.platform,
                benchmark_duration_seconds=self._benchmark_duration_seconds,
                constants=self._constants,
                build_variables=build_variables,
                record_data_dir=temp_record_data_dir,
                **run_variables,
            )

            if self._command_is_async():
                single_run_process: AsyncProcess = single_run_return
                for attachment in self._command_attachments:
                    attachment(
                        process=single_run_process,
                        record_data_dir=record_data_dir,
                    )
                single_run_output = single_run_process.output()
            else:
                single_run_output: str = single_run_return

            # If the host was remote, all the wrappers generated files on the remote machine and
            # these need to be copied back to the host machine.
            if not self.platform.comm.is_local:
                self.platform.comm.copy_to_host(f"{temp_record_data_dir}/", f"{record_data_dir}/")
                # Clean up nicely after ourselves
                self.platform.comm.remove(self._temp_record_prefix(), recursive=True)
            
            single_run_results = self.parse_output_to_results(
                command_output=single_run_output,
                build_variables=build_variables,
                run_variables=run_variables,
                benchmark_duration_seconds=self._benchmark_duration_seconds,
                record_data_dir=record_data_dir,
            )

            self._nb_runs_done += 1
            experiment_results_header = experiment_results

            if isinstance(single_run_results, list):
                # multi-line output record
                experiment_results_lines = []
                for line in single_run_results:
                    experiment_results_lines.append(dict_union(experiment_results_header, line))
            else:
                # single-line output record
                record_params_results = dict_union(experiment_results_header, single_run_results)
                experiment_results_lines = [record_params_results]

            def wrdr(file_content: str, filename: PathType) -> None:
                self._write_to_record_data_dir(
                    file_content=file_content,
                    filename=filename,
                    record_data_dir=record_data_dir,
                )

            for post_run_hook in self._post_run_hooks:
                hook_dict = post_run_hook(
                    experiment_results_lines=experiment_results_lines,
                    record_data_dir=record_data_dir,
                    write_record_file_fun=wrdr,
                )
                if hook_dict:
                    for xrline in experiment_results_lines:
                        xrline.update(hook_dict)

            wrdr(
                file_content=json.dumps(experiment_results_lines, indent=4).strip() + "\n",
                filename="experiment_results.json",
            )

            with open(self._csv_output_path, "a") as csv_output_file:
                for experiment_results_line in experiment_results_lines:
                    sep = CSV_SEPARATOR
                    if not self._first_line_is_printed:
                        header_list = list(experiment_results_line.keys())
                        current_thread_columns = [
                            int(c.split("thread_")[-1])
                            for c in header_list
                            if c.startswith("thread_")
                        ]

                        thread_list = []
                        if len(current_thread_columns) > 0:
                            current_max_thread = max(current_thread_columns)
                            thread_list = [
                                f"thread_{t}"
                                for t in range(current_max_thread + 1, self._max_nb_threads())
                            ]
                        header = sep.join(header_list + thread_list)

                        teeprint(content=header, file=csv_output_file)
                        self._first_line_is_printed = True
                    current_line = sep.join(map(str, experiment_results_line.values()))
                    teeprint(content=current_line, file=csv_output_file)

    def _record_data_dir(
        self,
        record_parameters: Dict[str, str | int | float],
        run_id: int,
    ) -> Optional[pathlib.Path]:
        if self._base_data_dir is None:
            return None
        bdd: pathlib.Path = self._base_data_dir

        total_nb_runs = self._nb_runs
        max_nb_digits = len(str(total_nb_runs))
        nb_run_str = f"{run_id:0{max_nb_digits}}"

        dirnames = [f"{k}-{v}" for k, v in record_parameters.items()] + [f"run-{nb_run_str}"]
        result = bdd.joinpath(*dirnames).resolve()

        if not result.is_dir():
            os.makedirs(result)

        return result

    def _log_headers(
        self,
        output_file,
        experiment_name,
        benchmark_duration_seconds,
        nb_runs,
        start_time,
        expected_duration_seconds,
    ) -> None:
        def log_line(line, nb_dashes=1):
            dashes_str = "#" * nb_dashes
            print(f"{dashes_str} {line}", file=output_file)

        def git_command(command):
            output = "N/A"
            try:
                if self.platform.comm.path_exists(path=self.bench_src_path):
                    output = self.platform.comm.shell(
                        command=command,
                        current_dir=self.bench_src_path,
                        print_input=False,
                        print_output=False,
                    )
            except CalledProcessError:
                pass
            result = output.strip()
            return result

        log_line(f"benchmark_campaign_name: {experiment_name}")
        log_line(f"benchmark_duration_seconds: {benchmark_duration_seconds}")
        log_line(f"nb_runs: {nb_runs}")

        date_val = start_time.strftime("%Y%m%d_%H%M%S")
        log_line(f"date: {start_time}")
        log_line(f"date_val: {date_val}")

        branch = git_command("git rev-parse --abbrev-ref HEAD")
        sha = git_command("git rev-parse HEAD")
        log_line(f"git_branch: {branch}")
        log_line(f"git_sha: {sha}")

        kernel_full = self.platform.comm.shell(command="uname -a").strip()
        log_line(f"kernel: {kernel_full}")

        boot_args = get_boot_args()
        log_line(f"kernel_boot_args: {boot_args}")

        if self.tilt is not None:
            tilt_compiler = self.tilt.get_compiler()
            tilt_exact_compiler = self.tilt.get_exact_compiler()
            log_line(f"tilt_compiler: {tilt_compiler}")
            log_line(f"tilt_exact_compiler: {tilt_exact_compiler}")

        if expected_duration_seconds is not None:
            expected_duration_pretty = seconds2pretty(expected_duration_seconds)
            log_line(f"expected_duration_seconds: {expected_duration_seconds}")
            log_line(f"expected_duration_pretty: {expected_duration_pretty}")

    def _command_is_async(self) -> bool:
        return len(self._command_attachments) > 0

    def _run_async_bench_command(
        self,
        wrapped_run_command: SplitCommand,
        current_dir: PathType,
        wrapped_environment: Environment,
        **kwargs,
    ) -> AsyncProcess:
        if "record_data_dir" in kwargs:
            record_data_dir = pathlib.Path(kwargs["record_data_dir"])
            stdout_path = record_data_dir / "cmd_stdout.txt"
            stderr_path = record_data_dir / "cmd_stderr.txt"
        else:
            stdout_path = "/tmp/benchkit_lastcmd_stdout.txt"
            stderr_path = "/tmp/benchkit_lastcmd_stderr.txt"

        current_process = shell_async(
            command=wrapped_run_command,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            platform=self.platform,
            current_dir=current_dir,
            environment=wrapped_environment,
        )

        return current_process

    def _get_run_variable_default(
        self,
        name: RecordKey,
    ) -> RecordValue:
        signature = inspect.signature(self.single_run)
        parameters = signature.parameters
        parameter = parameters[name]
        result = parameter.default
        return result

    def _get_run_variable_value(
        self,
        name: RecordKey,
        run_variables: RecordParameters,
    ) -> RecordValue:
        if name in run_variables:
            return run_variables[name]
        return self._get_run_variable_default(name=name)
