# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for the Graph500 benchmark.
See: https://github.com/graph500/graph500
"""

import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType


class Graph500Bench(Benchmark):
    """Benchmark object for Graph500 benchmark."""

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

        bench_src_path = pathlib.Path(src_dir / "src")
        if not self.platform.comm.isdir(bench_src_path) or not self.platform.comm.isfile(bench_src_path / "Makefile"):
            raise ValueError(f"Invalid Graph500 source path: {bench_src_path}\n")
        
        self._bench_src_path = bench_src_path

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return ["non_power_of_two"]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "version",
            "scale",
            "skip_validation",
            "skip_bfs"
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            # A valid MPI-3 library needs to be available
            PackageDependency("mpich"),
        ]

    def prebuild_bench(self, **_kwargs) -> None:
        pass

    def build_bench(
        self,
        non_power_of_two: bool = False,
        **kwargs,
    ) -> None:
        
        # we need to make a small change to the makefile in order to set non_power_of_two
        # see https://github.com/graph500/graph500/blob/newreference/README
        makefile_path = self._bench_src_path / "Makefile"
        makefile = self.platform.comm.read_file(makefile_path)
        lines = makefile.splitlines()
        # make sure the flag set correctly
        for index, line in enumerate(lines):
            if line.startswith("LDFLAGS"):
                if non_power_of_two:
                    lines[index] = line + " -DPROCS_PER_NODE_NOT_POWER_OF_TWO"
                else:
                    lines[index] = line.replace("-DPROCS_PER_NODE_NOT_POWER_OF_TWO", "")
        
        # save it to the file
        self.platform.comm.write_content_to_file("\n".join(lines), makefile_path)
        # build
        self.platform.comm.shell(
            command=f"make{self._parallel_make_str()}",
            current_dir=self._bench_src_path,
            output_is_log=True,
        )
        # reset the file to its original contents
        self.platform.comm.write_content_to_file(makefile, makefile_path)

    def clean_bench(self) -> None:
        self.platform.comm.shell(["make", "clean"], current_dir=self.bench_src_path)

    def single_run(
        self,
        version: str = "bfs",
        scale: int = 1,
        skip_validation: bool = False,
        skip_bfs: bool = False,
        **kwargs,
    ) -> str:
        
        environment = self._preload_env(**kwargs)
        
        # set the environment correctly
        if environment is None: environment = dict()
        environment["SKIP_VALIDATION"] = "1" if skip_validation else "0"
        environment["SKIP_BFS"] = "1" if skip_bfs else "0"
        
        if version not in ["bfs", "bfs_sssp"]:
            raise Exception("Invalid value given for version:", version, "given, but only bfs and bfs_sssp are accepted.")

        run_command = [
            "./graph500_reference_" + version,
            str(scale),
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

    def parse_output_to_results(
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
        lines = command_output.splitlines()
        result_dict = dict()
        
        for line in lines:
            if ':' in line:
                # result lines look like:
                # KEY:        VALUE
                parts = line.split(':')
                key = parts[0].strip()
                value = float(parts[-1].replace("!", "").strip())
                result_dict[key] = value

        return result_dict
    

def graph500_campaign(
    name: str = "graph500_campaign",
    benchmark: Optional[Graph500Bench] = None,
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
    
    version: Iterable[str] = (),
    scale: Iterable[int] = (),
    skip_validation: Iterable[bool] = (),
    skip_bfs: Iterable[bool] = (),
    non_power_of_two: Iterable[bool] = (),
    
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the LevelDB benchmark."""
    
    variables = {
        "version": version,
        "scale": scale,
        "skip_validation": skip_validation,
        "skip_bfs": skip_bfs,
        "non_power_of_two": non_power_of_two,
    }
    
    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        raise Exception("src_dir is required")

    if benchmark is None:
        benchmark = Graph500Bench(
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
