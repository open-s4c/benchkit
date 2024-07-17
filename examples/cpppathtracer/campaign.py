import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants, CampaignSuite
from benchkit.commandwrappers import CommandWrapper
from benchkit.commandwrappers.strace import StraceWrap
from benchkit.commandwrappers.env import EnvWrap
from benchkit.commandwrappers.perf import PerfReportWrap, PerfStatWrap, enable_non_sudo_perf
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType, Environment
from benchkit.platforms import get_remote_platform, get_current_platform

RUN_REMOTELY = False
REMOTE_ADDR = "ssh://root@example.com:2222"

# See below where variables are specified on why these variables are necessary
BUILD_VARIABLES = [
    "threading_implementation",
    "use_color_buffer_per_thread",
    "use_slim_bvh_nodes",
    "triangle_intersection_algo",
    "work_square_size",
    "aabb_hit_implementation",
    "bvh_first_hit_caching",
    "bvh_sah"
]
RUN_VARIABLES = ["nb_threads", "preset"]


class ForgetFullException(Exception):
    pass


class RayTracerBenchmark(Benchmark):
    """Benchmark object for main benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        bench_src_dir: PathType | None = None,
        copy_src_to_build: bool = False,
        command_wrappers: Iterable[CommandWrapper] = [],
        command_attachments: Iterable[CommandAttachment] = [],
        shared_libs: Iterable[SharedLib] = [],
        pre_run_hooks: Iterable[PreRunHook] = [],
        post_run_hooks: Iterable[PostRunHook] = [],
        platform: Platform = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        self._src_dir = src_dir
        self._bench_src_path = bench_src_dir
        if platform is not None:
            self.platform = platform

        # If this is on a remote machine, copy the source to the remote machine
        if not copy_src_to_build:
            return

        # We need trailing slashes to make sure the directories are not copied in each other and
        # rather the files are synced between the directories
        src = pathlib.Path(self._src_dir)
        dst = pathlib.Path(self._bench_src_path)

        folders_to_copy = ["src", "include", "benchmarking/cornell"]

        files_to_copy = [
            "build.sh",
            "CMakeLists.txt",
            "custom_config.h",
            "benchmarking/suzanne_on_table.glb",
            "benchmarking/suzanne_on_table_hr.glb",
        ]

        # If you want to copy a folder, you need to append it with a leading / to make sure
        # that the contents are not copied and that the folders are not copied into each other.
        # Since pathlib does not support this (it auto strips trailing slashes), you have
        # to add them manually.
        for folder in folders_to_copy:
            self.platform.comm.copy_from_host(f"{src / folder}/", f"{dst / folder}/")

        for file in files_to_copy:
            self.platform.comm.copy_from_host(f"{src / file}", f"{dst / file}")

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return BUILD_VARIABLES

    @staticmethod
    def get_run_var_names() -> List[str]:
        return RUN_VARIABLES

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    @staticmethod
    def _parse_results(
        output: str,
        nb_threads: int,
    ) -> Dict[str, str]:
        return {}

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("cmake"),
        ]

    def prebuild_bench(self, **kwargs):
        pass

    def build_bench(self, **kwargs) -> None:
        # Create the config file that sets the build parameters
        custom_config = "#pragma once\n"
        for v in BUILD_VARIABLES:
            custom_config += f"#define {v.upper()} {kwargs.get(v)}\n"

        self.platform.comm.write_content_to_file(
            custom_config, pathlib.Path(self._bench_src_path) / "custom_config.h"
        )

        self.platform.comm.shell(
            command="./build.sh",
            current_dir=self._bench_src_path,
        )

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        record_data_dir: PathType,
        preset: str,
        nb_threads: int = 2,
        **kwargs,
    ) -> str:

        run_command = [
            "./raytracer",
            "--threads",
            str(nb_threads),
            "--preset",
            preset,
            "--outfile",
            str(record_data_dir / "benchmark.bmp"),

        ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment={},
            record_data_dir=record_data_dir,
            **kwargs,
        )

        output = self.run_bench_command(
            environment={},
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._bench_src_path,
            wrapped_environment=wrapped_environment,
            print_output=False,
            record_data_dir=record_data_dir,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        nb_threads = int(run_variables["nb_threads"])
        try:
            duration = command_output.splitlines()[-1].split(": ")[1].split()[0]
        except Exception:
            print(command_output)
            duration = "N/A"

        return {"nb_threads": nb_threads, "duration": duration}


def create_campaign(
    variables: Dict[str, List[str]],
    copy_src_to_build: bool,
    nb_runs: int,
    source_dir: str,
    bench_src_dir: str,
    platform: Platform | None = None,
):
    perfstat_wrapper = PerfStatWrap(freq=1000, separator=";", events=["cache-misses", "branch-misses"])

    benchmark = RayTracerBenchmark(
        src_dir=source_dir,
        copy_src_to_build=copy_src_to_build,
        bench_src_dir=bench_src_dir,
        command_wrappers=[
            perfstat_wrapper,
        ],
        platform=platform,
        post_run_hooks=[
            perfstat_wrapper.post_run_hook_update_results,
        ],
    )

    return CampaignCartesianProduct(
        name="Raytracer_benchmark",
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        gdb=False,
        debug=False,
        constants=None,
        enable_data_dir=True,
    )


def main():
    source_dir = "./CppPathTracer"
    bench_src_dir = "./CppPathTracer"
    copy_src_to_build = False

    if RUN_REMOTELY:
        platform = get_remote_platform(REMOTE_ADDR)
        bench_src_dir = "/tmp/CppPathTracer"
        copy_src_to_build = True
    else:
        platform = get_current_platform()

    enable_non_sudo_perf(platform.comm)

    # The variables that have to be iterated through for the benchmark

    variables = {
        "nb_threads": [16],
        "preset": ["fast_cornell_benchmark"],
        "threading_implementation": [2],
        "use_color_buffer_per_thread": [0],
        "triangle_intersection_algo": [1],
        "work_square_size": [1],
        "aabb_hit_implementation": [3],
        "bvh_first_hit_caching": [1],
        "bvh_sah": [1],
    }

    nb_runs = 5

    # This is just as a safety to make sure the variables specified
    # and passed to the cartesian product below are actually all used
    # in the benchmark.
    # Why? I am forgetfull and I wasted like 2 benchmark hours because
    # of
    for v in variables.keys():
        if v not in BUILD_VARIABLES + RUN_VARIABLES:
            raise ForgetFullException(
                "You forgot to use the variables set here in the benchmark"
            )

    campaign = create_campaign(
        variables=variables,
        copy_src_to_build=copy_src_to_build,
        nb_runs=nb_runs,
        source_dir=source_dir,
        bench_src_dir=bench_src_dir,
        platform=platform,
    )
    campaigns = [campaign]

    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
