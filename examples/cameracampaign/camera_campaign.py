import pathlib
from typing import Any, Dict, Iterable, List, Optional
from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct
from benchkit.commandwrappers import CommandWrapper
from benchkit.commandwrappers.perf import PerfStatWrap
from benchkit.commandwrappers.strace import StraceWrap
from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform, get_remote_platform, get_current_platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType
from benchkit.utils.dir import caller_dir
from pythainer.examples.builders import get_user_gui_builder
from pythainer.examples.installs import realsense2_lib_install_from_src, opencv_lib_install_from_src
from pythainer.examples.runners import gui_runner, camera_runner, personal_runner
from pythainer.runners import ConcreteDockerRunner
import re

DOCKER = True
REMOTE = False
REMOTE_HOST = "kr260"
NB_RUNS = 3


class CameraOCCBench(Benchmark):
    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
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

        # Use pass as a placeholder if method's body is not yet implemented
        self._src_dir = src_dir
        self._bench_src_path = pathlib.Path(src_dir)

    def prebuild_bench(self, **kwargs):
        build_dir = (self._src_dir / "build").resolve()
        self.platform.comm.makedirs(path=build_dir, exist_ok=True)

        cmake_command = ['cmake', str(self._src_dir), '-B', str(build_dir)]
        print(f"Running CMake: {' '.join(cmake_command)}")
        self.platform.comm.shell(
            command=cmake_command,
            current_dir=build_dir,
            output_is_log=True,
        )
        self.platform.comm.shell(command=cmake_command, current_dir=build_dir)

        make_command = ['make']
        print(f"Running Make: {' '.join(make_command)}")
        self.platform.comm.shell(
            command=make_command,
            current_dir=build_dir,
            output_is_log=True,
        )
        self.platform.comm.shell(command=make_command, current_dir=build_dir)

    def build_bench(self, **kwargs) -> None:
        pass

    def single_run(
        self,
        duration_seconds: int,
        **kwargs,
    ) -> str:
        environment = self._preload_env(
            duration_seconds=duration_seconds,
            **kwargs
        )
        run_command = [
            "./CameraProcessing",
            f"{duration_seconds}",
        ]
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            duration_seconds=duration_seconds,
            **kwargs
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=(self._src_dir / "build").resolve(),
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        return output

    def parse_output_to_results(
        self,
        command_output: str,
        build_variables: Dict[str, Any],
        run_variables: Dict[str, Any],
        benchmark_duration_seconds: int,
        record_data_dir: PathType,
        **kwargs,
    ):
        benchmark_duration_seconds = int(run_variables["benchmark duration seconds"])# TODO?
        match = re.search(r"Final counter value: (\d+)", command_output)
        if match:
            # Extract the number from the matched group and convert it to an integer
            final_counter_value = int(match.group(1))

            # Calculate the result by dividing the final counter value by the duration
            result_per_second = final_counter_value / benchmark_duration_seconds
            output = {"throughput": result_per_second}
            return output

    def get_build_var_names(self) -> List[str]:
        return []

    def get_run_var_names(self) -> List[str]:
        return [
            "duration_seconds",
        ]

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path


def get_docker_platform(
    user_name: str,
    host_src_dir: PathType,
    guest_src_dir: PathType,
) -> Platform:
    image_name = "camerabenchkit"
    lib_dir = f"/home/{user_name}/libraries"

    docker_builder = get_user_gui_builder(
        image_name=image_name,
        base_ubuntu_image="ubuntu:22.04",
        user_name=user_name,
        lib_dir=lib_dir,
    )
    docker_builder.space()

    opencv_lib_install_from_src(
        builder=docker_builder,
        workdir=lib_dir,
        commit_main="4.8.1",
        commit_contrib="4.8.1",
        debug=False,
    )
    docker_builder.space()

    realsense2_lib_install_from_src(
        builder=docker_builder,
        workdir=lib_dir,
        debug=False,
    )
    docker_builder.space()

    docker_builder.root()
    docker_builder.desc("Symbolic link to find eigen3 folder")
    docker_builder.run(command="ln -s /usr/include/eigen3/Eigen /usr/include/Eigen")
    docker_builder.user()

    docker_builder.build()

    # TODO use builtin runner: docker_builder.get_runner()
    docker_runner = ConcreteDockerRunner(
        image=image_name,
        environment_variables={},
        volumes={f"{host_src_dir}": f"{guest_src_dir}"},
        devices=[],
        network="host",
        workdir=guest_src_dir,
    )
    docker_runner |= gui_runner() | camera_runner() | personal_runner()

    comm = DockerCommLayer(docker_runner=docker_runner)
    platform = Platform(comm_layer=comm)

    return platform


def main() -> None:
    command_wrappers = []

    if REMOTE:
        bench_src_path = caller_dir()  # TODO
        platform = get_remote_platform(host=REMOTE_HOST, environment=None)
        extend_wrappers = False
    elif DOCKER:
        host_src_dir = caller_dir()
        guest_src_dir = pathlib.Path("/home/nima/bench")
        platform = get_docker_platform(
            user_name="nima",
            host_src_dir=host_src_dir,
            guest_src_dir=guest_src_dir,
        )
        bench_src_path = guest_src_dir
        extend_wrappers = False  # TODO perf in docker
    else:
        bench_src_path = caller_dir()
        platform = get_current_platform()
        extend_wrappers = True

    if extend_wrappers:
        events = ['branch-misses', 'cache-misses', 'cpu-cycles']
        command_wrappers.append(PerfStatWrap(events=events))
        command_wrappers.append(StraceWrap())

    campaign = CampaignCartesianProduct(
        name="camera_campaign",
        benchmark=CameraOCCBench(
            src_dir=bench_src_path,
            command_wrappers=command_wrappers,
            platform=platform,
        ),
        nb_runs=NB_RUNS,
        variables={
            "duration_seconds": list(range(1, 31)),
        },
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
        benchmark_duration_seconds=None,
    )
    campaign.run()

    campaign.generate_graph(
        plot_name="lineplot",
        x="duration_seconds",
        y="throughput",
    )


if __name__ == "__main__":
    main()
