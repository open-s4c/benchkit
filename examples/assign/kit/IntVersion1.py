#!/usr/bin/env python3
from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.commandwrappers.perf import PerfStatWrap
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform, get_current_platform, get_remote_platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType
from benchkit.utils.dir import get_curdir, parentdir
from benchkit.utils import parselog, systemactions
from benchkit.shell.shell import shell_out
import os
import pathlib
import time

from typing import Any, Dict, Iterable, List, Optional

class ThreadCounterBench(Benchmark):

    def __init__(
        self,
        command_wrappers: Iterable[CommandWrapper] = [],
        command_attachments: Iterable[CommandAttachment] = [],
        shared_libs: Iterable[SharedLib] = [],
        pre_run_hooks: Iterable[PreRunHook] = [],
        post_run_hooks: Iterable[PostRunHook] = [],
        platform: Platform = [],
        build_dir: PathType | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            pre_run_hooks=pre_run_hooks,
            shared_libs=shared_libs,
            post_run_hooks=post_run_hooks,
        )

        self.platform = get_current_platform()  # TODO Warning! overriding upper class platform
        # self.platform = get_remote_platform(host="localhost")
        script_path = get_curdir(__file__)
        bench_path = script_path
        print(bench_path)
        # Benchmar directory?
        self._bench_src_path = bench_path

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path
    
    def clean_bench(self) -> None:
        pass
    
    @staticmethod
    def get_run_var_names():
        return [
            "size",
            "itterations"    
        ]
    
    @staticmethod
    def get_build_var_names():
        return []
    
    @staticmethod
    def _parse_results(
        log_output: str,
        itterations: int,
        size: int
    ) -> Dict[str, Any]:
        
        duration = int(log_output)
        
        measurement_dict = {
            "itterations": itterations,
            "size": size,
            "duration": duration,
            "throughput": itterations/duration,
            "sizedthroughput": (itterations* size * size)/duration
        }

        return measurement_dict
    
    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        size = int(run_variables["size"])
        itterations = int(run_variables["itterations"])
        result_dict = self._parse_results(log_output=command_output, itterations=itterations, size=size)
        return result_dict

    def build_bench(
        self,
        **kwargs,
    ):
        build_dir = self._build_dir
        self.platform.comm.shell(
            command=f"make",
            current_dir=build_dir,
            output_is_log=True,
        )


    def single_run(  # pylint: disable=arguments-differ
        self,
        size: int,
        itterations: int,
        **_kwargs,
    ):
        environment = {}

        command = ["./IntVersion", "-seed", str(90), "-i", str(itterations), "-s", str(size)]
        wrap_run_command, wrapperd_environment = self._wrap_command(
            run_command=command,
            environment=environment,
            **_kwargs
        )

        output = self.run_bench_command(
            run_command=command,
            wrapped_run_command=wrap_run_command,
            wrapped_environment=wrapperd_environment,
            environment=environment,
            current_dir=self._bench_src_path,
            print_output=False,
            **_kwargs
        )

        return output
    
    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []
    
    def prebuild_bench(self, **_kwargs) -> None:
        pass
    

def intversion_campaign(
    name: str = "campaign",
    benchmark: Optional[ThreadCounterBench] = None,
    src_dir: Optional[PathType] = None,
    build_dir: Optional[str] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    size: Iterable[int] = (1,),
    itterations: Iterable[int] = (1,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the LevelDB benchmark."""
    variables = {
        "size": size,
        "itterations": itterations,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = ThreadCounterBench(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
            build_dir=build_dir,
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
        pretty=pretty
    )