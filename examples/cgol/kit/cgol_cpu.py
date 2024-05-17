"""
Benchkit support for Conway's game of life benchmark.
See: https://github.com/guido589/conway-game-of-life-parallel
"""

import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import get_current_platform
from benchkit.platforms.generic import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import Constants, PathType

class CGOLBench(Benchmark):
    """Benchmark object for Conway's Game Of Life benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        platform: Platform | None = None,
        build_dir: PathType | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform
        else:
            self.platform = get_current_platform()

        bench_src_path = pathlib.Path(src_dir)
        if build_dir is not None:
            self._build_dir = build_dir
        else:
            self._build_dir = bench_src_path / "build"
        self._bench_src_path = bench_src_path

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path
    

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("cmake"),
        ]

    @staticmethod
    def get_build_var_names():
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "bench_name",
            "nb_threads",
            "size",
            "nb_generations",
        ]
    
    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []
    
        
    def clean_bench(self) -> None:
        pass

    def prebuild_bench(self, **_kwargs) -> None:
        build_dir = self._build_dir
        self.platform.comm.makedirs(path=build_dir, exist_ok=True)

        self.platform.comm.shell(
            command=f"cmake ..",
            current_dir=build_dir,
            output_is_log=True,
        )
        self.platform.comm.shell(
            command=f"make{self._parallel_make_str()}",
            current_dir=build_dir,
            output_is_log=True,
        )
    
    def build_bench(self, **_kwargs) -> None:
        pass

    def single_run( 
        self,
        benchmark_duration_seconds: int,
        nb_threads: int = 2,
        size: int = 100,
        bench_name: str = "time_based",
        nb_generations: int = 5,
        **_kwargs,
    ):
        environment = {}
        duration_flag = []
        if bench_name == "time_based":
            duration_flag = ["-d", f"{benchmark_duration_seconds}"]
        elif bench_name == "generation_based":
            duration_flag = ["-g", f"{nb_generations}"]
        else:
            raise ValueError(f"Unknown bench_name: {bench_name}")
        width = size
        height = size
        run_command = [
            f"./cgol",
            "-t", f"{nb_threads}",
            "-w", f"{width}",
            "-h", f"{height}",
            *duration_flag
        ]
        wrap_run_command, wrapperd_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **_kwargs
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrap_run_command,
            current_dir=self._build_dir,
            environment=environment,
            wrapped_environment=wrapperd_environment,
            print_output=False
        )
        return output
    
    @staticmethod
    def _parse_results(
        log_output: str,
        benchmark_duration_seconds: int
    ) -> Dict[str, Any]:
        
        nb_cells_updated_pattern = "Number of cells updated: (\d+)"
        nb_cells_updated = re.search(nb_cells_updated_pattern, log_output).group(1)

        return {
            "global_count": int(nb_cells_updated),
            "duration": benchmark_duration_seconds,
        }
    
    def parse_output_to_results(
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        benchmark_duration_seconds: int,
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = self._parse_results(log_output=command_output, benchmark_duration_seconds=benchmark_duration_seconds)
        return result_dict
    
def cgol_campaign(
    name: str = "cgol_campaign",
    benchmark: Optional[CGOLBench] = None,
    bench_name: Iterable[str] = ("",),
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
    nb_generations: Iterable[int] = (100,),
    nb_threads: Iterable[int] = (1,),
    size: Iterable[int] = (100,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the cgol benchmark."""
    variables = {
        "bench_name": bench_name,
        "nb_threads": nb_threads,
        "size": size,
        "nb_generations": nb_generations,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass

    if benchmark is None:
        benchmark = CGOLBench(
            src_dir=src_dir,
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
        pretty=pretty,
    )