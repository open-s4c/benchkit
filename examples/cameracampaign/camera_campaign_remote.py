import pathlib
from typing import Any, Dict, Iterable, List, Optional
import subprocess
from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.commandwrappers.perf import PerfStatWrap
from benchkit.commandwrappers.strace import StraceWrap
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.platforms import *
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType
from benchkit.shell.shell import shell_out
import re

class camera_OCC(Benchmark):

    def __init__(self,
                 src_dir: PathType,
                 command_wrappers: Iterable[CommandWrapper],
                 command_attachments: Iterable[CommandAttachment],
                 shared_libs: Iterable[SharedLib],
                 pre_run_hooks: Iterable[PreRunHook],
                 post_run_hooks: Iterable[PostRunHook],
                 platform: Platform | None = None,
                 build_dir: PathType | None = None) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        print(f"platform equal={self.platform}")

        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform

        # Use pass as a placeholder if method's body is not yet implemented
        self.src_dir = src_dir
        self._bench_src_path = pathlib.Path(src_dir)

    def prebuild_bench(self, **kwargs):
        # Ensure the build directory exists
        self.build_dir = (self.src_dir / "build").resolve()
        self.platform.comm.makedirs(path=self.build_dir, exist_ok=True)

        # Print the source directory for verification
        print(f"Source directory: {self.src_dir}")

        # Run CMake to configure the build system
        cmake_command = ['cmake', str(self.src_dir), '-B', str(self.build_dir)]
        print(f"Running CMake: {' '.join(cmake_command)}")
        self.platform.comm.shell(
            command=cmake_command,
            current_dir=self.build_dir,
            output_is_log=True,
        )
        self.platform.comm.shell(command=cmake_command, current_dir=self.build_dir)

        # Run Make to build the project
        make_command = ['make']
        print(f"Running Make: {' '.join(make_command)}")
        self.platform.comm.shell(
            command=make_command,
            current_dir=self.build_dir,
            output_is_log=True,
        )
        self.platform.comm.shell(command=make_command, current_dir=self.build_dir)

        # Print the build directory for verification
        print(f"Build directory: {self.build_dir}")

    def single_run(self, benchmark_duration_seconds: int, cpu_order: CpuOrder = None,
                   use_lse: bool = False, atomics: Optional[str] = None, master_thread_core: Optional[int] = None,
                   **kwargs) -> str:

        print(kwargs)
        environment = self._preload_env(
            use_lse=use_lse,
            atomics=atomics,
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            **kwargs
        )
        run_command = [
            "./CameraProcessing",  # The executable for your benchmark
            f"{benchmark_duration_seconds}",  # Pass duration as an argument
        ]
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            **kwargs
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self.build_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )
        print(" the output is:", output)

        self.output = output

    def parse_results(self,
                      benchmark_duration_seconds: int):

        match = re.search(r"Final counter value: (\d+)", self.output)
        if match:
            # Extract the number from the matched group and convert it to an integer
            final_counter_value = int(match.group(1))

            # Calculate the result by dividing the final counter value by the duration
            result_per_second = final_counter_value / benchmark_duration_seconds
            print("throughput is :", result_per_second)
            output = {"throughput": result_per_second}
            return output

    def get_build_var_names(self) -> List[str]:
        return []

    def get_run_var_names(self) -> List[str]:
        return [
            "benchmark duration seconds",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return [
            "lock",
            "atomics",
            "use_lse",
        ]

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    def build_bench(
            self,
            **kwargs,
    ) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    def parse_output_to_results(self, run_variables: Dict[str, Any], **_kwargs) -> Dict[str, Any]:
        benchmark_duration_seconds = int(run_variables["benchmark duration seconds"])  # default to 5 if not specified
        result_dict = self.parse_results(benchmark_duration_seconds=benchmark_duration_seconds)
        return result_dict


def  main(benchmark_duration):
    events=['branch-misses','cache-misses','cpu-cycles']
    wrapper_perf=PerfStatWrap(events=events)
    wrapper_strace = StraceWrap()
    benchmark_duration_seconds = benchmark_duration
    NB_RUNS=3
    kernel = shell_out("uname -r").strip()
    campaign = CampaignCartesianProduct(
        name="camera_campaign",
        benchmark=camera_OCC(

            src_dir=pathlib.Path("/home/ubuntu/benchkit/cameracampaign/"), #replace with the actual path 
            command_wrappers= [],
            command_attachments=[],
            shared_libs=[],
            pre_run_hooks=[],
            post_run_hooks=[],
            platform= get_remote_platform(host="",environment=None),
            build_dir=None,

        ),
        nb_runs=NB_RUNS,
        variables={
            "benchmark duration seconds": [benchmark_duration_seconds]
        },
        constants={
            "kernel": kernel,
        },
        debug=False,
        gdb=False,
        enable_data_dir=True,
        benchmark_duration_seconds=benchmark_duration_seconds,
    )
    campaign.run()
    return campaign

if __name__ == "__main__":
    for i in range(1,30):
        main(i)
