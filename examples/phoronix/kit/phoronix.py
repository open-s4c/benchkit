"""
Benchkit support for Phoronix test profiles.
"""

import pathlib
from typing import Any, Dict, Iterable, List, Optional
from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType
from parse import PhoronixTestSuite
import subprocess
import os
import re


class PhoronixTestProfileBench(Benchmark):
    """Benchmark object for a Phoronix Test Profile benchmark."""

    def __init__(
            self,
            test_profile_src_dir: PathType,
            command_wrappers: Iterable[CommandWrapper],
            command_attachments: Iterable[CommandAttachment],
            shared_libs: Iterable[SharedLib],
            pre_run_hooks: Iterable[PreRunHook],
            post_run_hooks: Iterable[PostRunHook],
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks
        )

        self._test_profile_src_dir = pathlib.Path(test_profile_src_dir)
        # load the profile
        self._profile = PhoronixTestSuite.create_from_path(self._test_profile_src_dir)
        # some benchmarks expect all of the environment variables to be available
        self._env = os.environ.copy()
        # we also need to set the home variable for the lifecycle scripts
        self._env["HOME"] = self._test_profile_src_dir

    def _get_name(self):
        """Gets the name of the test profile."""
        
        name_with_version = str(self._test_profile_src_dir).split("/")[-1].split("-")
        name_with_version.pop()
        return "-".join(name_with_version)

    def _get_executable_name(self):
        """Gets the name of the executable."""
        
        if self._profile.test_def is not None and self._profile.test_def.test_information.executable is not None:
            return str(self.bench_src_path / self._profile.test_def.test_information.executable)
        
        return "./" + self._get_name()

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._test_profile_src_dir
    
    @staticmethod
    def get_build_var_names() -> List[str]:
        return []
    
    def get_run_var_names(self) -> List[str]:
        if self._profile.test_def is not None and self._profile.test_def.test_settings is not None:
            return list(map(lambda option: option.identifier, self._profile.test_def.test_settings.options))
        else:
            return []

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        deps = self._profile.test_def.test_profile.external_dependencies
        if deps is None:
            deps = []
        return super().dependencies() + list(map(lambda dep: PackageDependency(dep), deps))

    def build_tilt(self, **kwargs) -> None:
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs) -> None:
        # download the files
        if self._profile.downloads:
            for download in self._profile.downloads.downloads:
                download.ensure_exists(self.bench_src_path)

        if self._profile.pre is not None:
            subprocess.call(["sh", self._profile.pre], cwd=self.bench_src_path, env=self._env)

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        # call the install script on the build step
        if self._profile.install is not None:
            subprocess.call(["sh", self._profile.install], cwd=self.bench_src_path, env=self._env)

    def clean_bench(self) -> None:
        # call the interim script when cleaning
        if self._profile.interim is not None:
            subprocess.call(["sh", self._profile.interim], cwd=self.bench_src_path, env=self._env)

    
    def _build_command(self, kwargs):
        """Builds the command that should be used to run the benchmark."""
        
        command = [self._get_executable_name()]
        test_def = self._profile.test_def
        
        if test_def is not None and test_def.test_settings is not None:
            if test_def.test_settings.options is not None:
                for option in test_def.test_settings.options:
                    # we build an additional argument
                    comm = ""
                    # add a prefix if it is defined
                    if option.argument_prefix is not None: comm += option.argument_prefix
                    # if the identifier is passed to the benchmark, add it but display a warning
                    # if we don't recognize it
                    if option.identifier in kwargs:
                        if kwargs[option.identifier] not in option.get_valid_values():
                            print("[WARNING]: Unexpected value received for", option.identifier)
                        comm += kwargs[option.identifier]
                    else:
                        # otherwise pick the first value
                        valid_values = option.get_valid_values()
                        if len(valid_values) > 0:
                            comm += valid_values[0]
                        else:
                            comm = ""
                    if comm == "": continue
                    # add a postfix if it is defined
                    if option.argument_postfix is not None: comm += option.argument_postfix
                    command.append(comm)
            
            if test_def.test_settings.default is not None:
                if test_def.test_settings.default.arguments is not None:
                    command.append(test_def.test_settings.default.arguments)
                if test_def.test_settings.default.post_arguments is not None:
                    command.append(test_def.test_settings.default.post_arguments)
                    
        return command

    def single_run(  # pylint: disable=arguments-differ
        self,
        **kwargs,
    ) -> str:
        if self._profile.interim is not None:
            subprocess.call(["sh", self._profile.interim], cwd=self.bench_src_path, env=self._env)

        # make sure to set the HOME and LOG_FILE env variables expected by test profiles
        environment = self._env
        environment["HOME"] = self._test_profile_src_dir 
        # benchmarks will output their results to a log file
        environment["LOG_FILE"] = self._test_profile_src_dir / "log"
        
        run_command = self._build_command(kwargs)
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._test_profile_src_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=True,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        """Parses the output to a results dictionary."""
        
        result_dict = dict()
        
        # for all the things we need to extract
        for index, results_parser in enumerate(self._profile.results_def.results_parsers):
            # get the command output from the log file
            command_output = (self._test_profile_src_dir / "log").read_text()
            
            if results_parser.delete_output_before is not None:
                command_output = command_output[command_output.find(results_parser.delete_output_before):]
            if results_parser.delete_output_after is not None:
                command_output = command_output[:command_output.find(results_parser.delete_output_after)]
            
            output_template = results_parser.output_template
            
            # we get all the result keys from the template
            regex = r"#_(.*?)_#"
            result_keys = list(map(lambda m: m.group(1), re.finditer(regex, output_template, re.MULTILINE)))
            
            results = dict()
            
            # and we create an array of parts we need to match
            parts = [output_template]
            for key in result_keys:
                last_el = parts.pop()
                parts_list = last_el.split("#_" + key + "_#")
                parts += parts_list
            
            # try to results in matching lines
            for line in command_output.splitlines():
                values = dict()
                failed = False
                
                for index in range(len(parts)):
                    if not line.startswith(parts[index]):
                        # the line does not start correctly
                        failed = True
                        break
                    if index + 1 == len(parts):
                        if line != parts[index]:
                            # the line does not end correctly
                            failed = True
                        break
                    
                    # extract the value
                    line = line[len(parts[index]):]
                    until = line.find(parts[index + 1])
                    if until == 0:
                        until = len(line)
                    # and add it to the results for this key
                    result = line[:until]
                    # perform transformations on the result if needed
                    if results_parser.strip_from_result is not None:
                        result = result.replace(results_parser.strip_from_result, "")
                    if results_parser.strip_result_postfix is not None and result.endswith(results_parser.strip_result_postfix):
                        result = result[:(len(result) - len(results_parser.strip_result_postfix))]
                    if results_parser.turn_chars_to_space is not None:
                        result = result.replace(results_parser.turn_chars_to_space, " ")
                    if results_parser.divide_result_by is not None:
                        try: result = float(result) / results_parser.divide_result_by
                        except Exception: pass
                    if results_parser.divide_result_divisor is not None:
                        try: result = float(result) // results_parser.divide_result_divisor
                        except Exception: pass
                    if results_parser.multiply_result_by is not None:
                        try: result = float(result) * results_parser.multiply_result_by
                        except Exception: pass
                    
                    if result_keys[len(values)] in values:
                        values[result_keys[len(values)]].append(result)
                    else:
                        values[result_keys[len(values)]] = [result]
                        
                    line = line[until:]
                
                # only add the results if the whole line matched
                if not failed:
                    for key, values in values.items():
                        if key in results:
                            results[key + str(index)].append(values)
                        else:
                            results[key + str(index)] = values
                    break
            
            # take the average if multimatch is used
            if results_parser.multi_match == "AVERAGE":
                for key, values in results:
                    try:
                        numbers_list = map(lambda v: float(v), values)
                        average = sum(numbers_list) / len(numbers_list)
                        results[key + str(index)] = [average]
                    except Exception:
                        pass
            
            result_dict = result_dict | results
            
        # convert multivalues to arrays
        for key, value in result_dict.items():
            if len(value) == 1:
                result_dict[key] = value[0]
            else:
                result_dict[key] = str(value)
    
        return result_dict


def phoronix_test_profile_campaign(
        name: str = "phoronix_campaign",
        benchmark: Optional[PhoronixTestProfileBench] = None,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        nb_runs: int = 1,
        constants: Constants = None,
        debug: bool = False,
        gdb: bool = False,
        enable_data_dir: bool = False,
        continuing: bool = False,
        benchmark_duration_seconds: int = 5,
        results_dir: Optional[PathType] = None,
        pretty: Optional[Dict[str, str]] = None,
        test_profile_src_dir: Optional[PathType] = None,
        
        **variables
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for a Phoronix test profile benchmark."""
    
    if benchmark is None:
        benchmark = PhoronixTestProfileBench(
            test_profile_src_dir=test_profile_src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )

    return CampaignCartesianProduct(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        constants=constants,
        debug=debug,
        gdb=gdb,
        enable_data_dir=enable_data_dir,
        continuing=continuing,
        benchmark_duration_seconds=benchmark_duration_seconds,
        results_dir=results_dir,
        pretty=pretty,
    )

