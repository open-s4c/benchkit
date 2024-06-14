# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Benchkit support for Membench benchmark.
See: https://github.com/nicktehrany/membench
"""

import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType


class MemBenchBench(Benchmark):
    """Benchmark object for MemBench benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        platform: Platform | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform

        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path):
            raise ValueError(
                f"Invalid MemBench source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        
        self._bench_src_path = bench_src_path

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "benchfile_name",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    @staticmethod
    def _parse_results(
        output: str
    ) -> Dict[str, str]:
        attributes = [
            'Engine', 'Flags', 'Iterations', 'Memcpy Iterations', 'Total Memcpy Calls',
            'Total Runtime', 'File Size', 'Copy Size', 'Random Read', 'Data Copied',
            'Minimum latency', 'Maximum latency', 'Average latency', 'Buffer Size'
        ]
        
        section_data = MemBenchBench.parse_section(output.strip())
        result = [section_data.get(attr, '') for attr in attributes]

        result_dict = dict(zip(attributes, result))

        return result_dict

    @staticmethod
    def convert_units(value):
        unit_conversions = {
            'GiB': ('MiB', 1024),
            'KiB': ('MiB', 1/1024),
            'sec': ('usec', 1e6),
            'msec': ('usec', 1e3),
            'nsec': ('usec', 1e-3),
            'usec': ('usec', 1),
        }
        for unit, (new_unit, factor) in unit_conversions.items():
            if unit in value:
                number = float(re.search(r'[\d.]+', value).group())
                converted_value = number * factor
                return f'{converted_value:.2f} {new_unit}'
        return value
    
    @staticmethod
    def parse_section(section):
        section_data = {}
        for line in section.strip().split('\n'):
            key, value = re.match(r'(.*?):\s*(.*)', line).groups()
            section_data[key] = MemBenchBench.convert_units(value)
        return section_data

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("make"),
            PackageDependency("gcc"),
        ]

    def build_tilt(self, **kwargs) -> None:
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs) -> None:
        pass

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        src_dir = self._bench_src_path
        
        # Make the project
        self.platform.comm.shell(
            command=f"make",
            current_dir=src_dir,
            output_is_log=True,
        )

        # Build benchmarking files to src_dir/out
        self.platform.comm.shell(
            command=f"touch benchfile",
            current_dir=src_dir,
            output_is_log=True,
        )

        # Generate file to be benchmarked
        # TODO using random values might introduce unpredictability in results, find a constant way
        self.platform.comm.shell(
            command=f"dd if=/dev/urandom of=benchfile bs=100M count=8",
            current_dir=src_dir,
            output_is_log=True,
        )

    def clean_bench(self) -> None:
        src_dir = self._bench_src_path

        # Generate file to be benchmarked
        self.platform.comm.shell(
            command=f"rm -f benchfile",
            current_dir=src_dir,
            output_is_log=True,
        )

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchfile_name: str = "",
        **kwargs,
    ) -> str:
        environment = self._preload_env(
            **kwargs,
        )

        file_path = self._bench_src_path / "examples" / benchfile_name
        
        run_command = [
            "./membench",
            f"-file={file_path}",
        ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._bench_src_path,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
       
        result_dict = self._parse_results(output=command_output)

        return result_dict


def membench_campaign(
    name: str = "membench_campaign",
    benchmark: Optional[MemBenchBench] = None,
    # Membench allows for granular control over benchmarks via files
    # When creating benchmarks, just created new ones inside the /examples folder
    # And include the file name in this list
    benchfile: Iterable[str] = ("example1.txt", "example2.txt"),  # Benchmark does not end: "example3.txt"
    # TODO remove the example and use the parameters as used in the examples directly with the command line
    src_dir: Optional[PathType] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the Membench benchmark."""

    variables = {
        "benchfile_name": benchfile,
    }

    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass

    if benchmark is None:
        benchmark = MemBenchBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
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
