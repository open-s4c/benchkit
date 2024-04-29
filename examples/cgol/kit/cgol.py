"""
Benchkit support for Conway's game of life benchmark.
See: https://github.com/guido589/perf-assignment
"""

import pathlib
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
            self.platform = platform  # TODO Warning! overriding upper class platform
        else:
            self.platform = get_current_platform()

        bench_src_path = pathlib.Path(src_dir)
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
        return [
            "version"
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "bench_name",
            "nb_threads",
            "width",
            "height",
            "nb_generations",
            "version",
        ]
    
    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []
    
        
    def clean_bench(self) -> None:
        pass

    def prebuild_bench(self, **_kwargs) -> None:
        pass
    
    def build_bench(self, version, **_kwargs) -> None:
        src_dir = self._bench_src_path
        build_dir = src_dir / version / "build"
        print(f"Building version {version} in {build_dir}")
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

    def single_run( 
        self,
        **_kwargs,
    ):
        return ""
    
    @staticmethod
    def _parse_results(
        log_output: str,
        nb_threads: int
    ) -> Dict[str, Any]:

        return {
            "nb_threads": nb_threads
        }
    
    def parse_output_to_results(
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        nb_threads = int(run_variables["nb_threads"])
        result_dict = self._parse_results(log_output=command_output, nb_threads=nb_threads)
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
    nb_threads: Iterable[int] = (1,),
    width: Iterable[int] = (100,),
    height: Iterable[int] = (100,),
    nb_generations: Iterable[int] = (100,),
    version: Iterable[str] = ("version-1",),
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
        "width": width,
        "height": height,
        "nb_generations": nb_generations,
        "version": version,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass  # TODO try some search heuristics

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