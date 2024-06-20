import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants, CampaignSuite
from benchkit.commandwrappers import CommandWrapper
from benchkit.commandwrappers.strace import StraceWrap
from benchkit.commandwrappers.env import EnvWrap
from benchkit.commandwrappers.perf import PerfReportWrap, PerfStatWrap
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType, Environment
from benchkit.platforms import get_remote_platform

# Use "blender" if you have blender in your path, otherwise use the
# exact path of the executable.
BLENDER_EXEC = "/opt/blender-4.1.1-linux-x64/blender"

RUN_REMOTELY = False
REMOTE_PATH = "ssh://root@example.com:2222"

RUN_VARIABLES = ["frame", "scene", "device", "samples"]


class ForgetFullException(Exception):
    pass


class BlenderBenchmark(Benchmark):
    """Benchmark object for blender benchmark."""

    def __init__(
        self,
        scenes_dir: PathType,
        bench_dir: PathType,
        outfile: str,
        copy_scenes_to_benchmark_dir: bool = False,
        command_wrappers: Iterable[CommandWrapper] = [],
        command_attachments: Iterable[CommandAttachment] = [],
        pre_run_hooks: Iterable[PreRunHook] = [],
        post_run_hooks: Iterable[PostRunHook] = [],
        platform: Platform = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=[],
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )

        self._bench_dir = pathlib.Path(bench_dir)
        self._outfile = pathlib.Path(outfile)

        if platform is not None:
            self.platform = platform

        # If this is on a remote machine, copy the scene to the remote machine
        if not copy_scenes_to_benchmark_dir:
            return

        # We need trailing slashes to make sure the directories are not copied in each other and
        # rather the files are synced between the directories
        src = pathlib.Path(scenes_dir)
        dst = self._bench_dir

        # If you want to copy a folder, you need to append it with a leading / to make sure
        # that the contents are not copied and that the folders are not copied into each other.
        # Since pathlib does not support this (it auto strips trailing slashes), you have
        # to add them manually.
        self.platform.comm.copy_from_host(f"{src}/", f"{dst}/")

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_dir

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return RUN_VARIABLES

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    @staticmethod
    def _parse_results() -> Dict[str, str]:
        return {}

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("blender")
        ]

    def prebuild_bench(self, **kwargs):
        pass

    def build_bench(self, **kwargs) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        record_data_dir: PathType,
        scene: str,
        frame: int,
        device: str,
        samples: int,
        **kwargs,
    ) -> str:

        run_command = [
            BLENDER_EXEC,
            "-b",
            str(self._bench_dir / scene),
            "--python-expr",
            f"import bpy ; bpy.data.scenes[\"Scene\"].cycles.samples = {samples}",
            "-o",
            str(record_data_dir / self._outfile),
            "-F",
            "PNG",
            "-f",
            str(frame),
            "--",
            "--cycles-device",
            device,
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
            current_dir=self._bench_dir,
            wrapped_environment=wrapped_environment,
            print_output=True,
            record_data_dir=record_data_dir,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        try:
            lines = command_output.splitlines()
            time = lines[-4].split(": ")[1].split()[0]
            time = time.split(":")
            if len(time) > 2:
                hours = time[0]
                minutes = time[1]
                seconds = time[2]
            else:
                hours = 0
                minutes = time[0]
                seconds = time[1]

            duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            duration = str(duration)

        except Exception:
            print(command_output)
            duration = "N/A"

        return {"duration": duration}

def create_campaign(
    variables: Dict[str, List[str]],
    copy_scenes_to_benchmark_dir: bool,
    nb_runs: int,
    scenes_dir: str,
    benchmark_dir: str,
    outfile: str,
    platform: Platform | None = None,
):
    benchmark = BlenderBenchmark(
        scenes_dir=scenes_dir,
        bench_dir=benchmark_dir,
        outfile=outfile,
        copy_scenes_to_benchmark_dir=copy_scenes_to_benchmark_dir,
        command_wrappers=[],
        platform=platform,
        post_run_hooks=[],
    )

    return CampaignCartesianProduct(
        name="blender_benchmark",
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        gdb=False,
        debug=False,
        constants=None,
        enable_data_dir=True,
    )


def main():
    scenes_dir = "."
    benchmark_dir = "."
    platform = None
    copy_scenes_to_benchmark_dir = False

    if RUN_REMOTELY:
        platform = get_remote_platform(REMOTE_PATH)
        benchmark_dir = "/tmp/blender-benchmark"
        copy_scenes_to_benchmark_dir = True

    # The variables that have to be iterated through for the benchmark
    variables = {
        # Which frame of the animation to render, in the example scene
        # use frame 80 since it uses a simulation that ends at frame 80.
        "frame": [80],
        # The scene/blendfile to render
        "scene": ["example-scene.blend"],
        # Valid options are: 'CPU' 'CUDA' 'OPTIX' 'HIP' 'ONEAPI' 'METAL'.
        # Select one that your machine can provide, nvidia CUDA or OPTIX
        # if you have a newer card, macOS uses METAL, AMD uses HIP.
        # Otherwise if you want to stress test a CPU, use CPU. It will
        # automatically select the maximum number of cores.
        # To use both the CPU and the GPU at the same time, add +CPU at
        # the end of the GPU device.
        "device": ["CUDA"],
        # Number of samples per pixel that have to be performed. This 
        # will have a MAJOR effect on runtime.
        "samples": [4096],
    }

    # Filename of the output image, the #'s are for file numbering
    outfile = "example-scene-####.png"

    nb_runs = 1

    # This is just as a safety to make sure the variables specified
    # and passed to the cartesian product below are actually all used
    # in the benchmark.
    # Why? I am forgetful and I wasted like 2 benchmark hours because
    # of this.
    for v in variables.keys():
        if v not in RUN_VARIABLES:
            raise ForgetFullException(
                "You forgot to use the variables set here in the benchmark"
            )

    campaign = create_campaign(
        variables=variables,
        copy_scenes_to_benchmark_dir=copy_scenes_to_benchmark_dir,
        nb_runs=nb_runs,
        scenes_dir=scenes_dir,
        benchmark_dir=benchmark_dir,
        platform=platform,
        outfile=outfile,
    )
    campaigns = [campaign]

    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
