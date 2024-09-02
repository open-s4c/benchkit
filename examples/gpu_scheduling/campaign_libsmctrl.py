#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import os
from typing import Any, Dict, List

from pythainer.examples.builders import get_user_gui_builder
from pythainer.examples.runners import gpu_runner, gui_runner, personal_runner
from pythainer.runners import ConcreteDockerRunner

from benchkit.benchmark import Benchmark
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import caller_dir
from benchkit.utils.types import PathType

from generate_config import generate_config

GUEST_SRC_DIR = "/home/user/src/cuda_scheduling_examiner_mirror"
GUEST_RESULTS_DIR = "/home/user/src/cuda_scheduling_examiner_mirror/results"

class GpuSchedulingBench(Benchmark):
    def __init__(
        self,
        platform: Platform,
        src_dir: PathType,
        results_dir: PathType,
    ) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=(),
        )
        self.platform = platform
        self._bench_src_path = pathlib.Path(src_dir)
        self._bench_results_path = pathlib.Path(results_dir)

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @property
    def bench_results_path(self) -> pathlib.Path:
        return self._bench_results_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            "kernel_names",
            "cthread_counts",
            "block_counts",
            "additional_infos",
            "release_times",
            "sm_masks",
            "data_sizes",
            "iterations"
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return []

    def build_bench(
        self,
        **kwargs,
    ) -> None:

        output_path = self._record_data_dir({key: kwargs[key] for key in self.get_build_var_names()},1)

        rel_output_path = output_path.relative_to(os.getcwd() + "/results")

        cuda_bench_config = generate_config(kwargs, rel_output_path)
        with open('./results/temp.conf', 'w') as file:
            file.write(cuda_bench_config)

    def single_run(
        self,
        **kwargs,
    ) -> str:
        current_dir = self.bench_src_path
        environment = self._preload_env(**kwargs)

        run_command = ["./bin/runner", "results/temp.conf"]
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=current_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=True,
            shell=True,
        )
        return output

    def parse_output_to_results(
        self,
        command_output: str,
        build_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        current_dir = self.bench_src_path

        output_path = self._record_data_dir(build_variables,1)

        rel_output_path = output_path.relative_to(os.getcwd())

        output_path = rel_output_path / "output"
        command = [
            f"python2",
            "./scripts/view_blocksbysm.py",
            "-v",
            "1200",
            "-w",
            "1200",
            "-d",
            f"{output_path}",
            "-o",
        ]
        self.platform.comm.shell(
            command=command,
            current_dir=current_dir,
        )

        return build_variables



def get_docker_platform() -> Platform:
    image_name = "gpuscheduler"
    builder = get_user_gui_builder(
        image_name=image_name,
        base_ubuntu_image="nvidia/cuda:11.4.3-devel-ubuntu20.04",
    )
    builder.space()

    builder.root()
    builder.desc("Remove annoying motd")
    builder.run(
        command=(
            r"find /opt/nvidia/entrypoint.d/ "
            r'\( -name "*.txt" -o -name "10-banner.sh" -o -name "12-banner.sh" \) '
            r"-exec rm {} +"
        )
    )
    builder.add_packages(packages=["python2", "python3", "python-tk", "python3-matplotlib"])
    builder.run("curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py")
    builder.run("python2 get-pip.py")
    builder.run("pip install canvasvg")
    builder.workdir("/home/user/src")
    builder.run(command="git clone http://rtsrv.cs.unc.edu/cgit/cgit.cgi/libsmctrl.git")
    builder.workdir("/home/user/src/libsmctrl")
    builder.run(command="make libsmctrl.a")
    builder.workdir("/home/user/src")
    builder.run(command="git clone https://github.com/JoshuaJB/cuda_scheduling_examiner_mirror.git -b rtas23-ae")
    builder.workdir("/home/user/src/cuda_scheduling_examiner_mirror")

    if pathlib.Path('./patches/cuda_scheduling_examiner_mirror_makefile.patch').is_file():
        builder.copy('cuda_scheduling_examiner_mirror_makefile.patch', '/home/user/src/cuda_scheduling_examiner_mirror')
        builder.run(command="git apply cuda_scheduling_examiner_mirror_makefile.patch")


    builder.copy('cuda_scheduling_examiner_mirror.patch', '/home/user/src/cuda_scheduling_examiner_mirror')
    builder.run_multiple(commands=["git apply cuda_scheduling_examiner_mirror.patch", "make all"])

    builder.root()
    builder.space()

    builder.user()
    builder.workdir("/home/user")
    builder.build(docker_context="./patches")

    host_src_dir = (caller_dir() / "results").resolve()

    # TODO use builtin runner
    # docker_runner = builder.get_runner()

    os.makedirs(host_src_dir, exist_ok=True)
    docker_runner = ConcreteDockerRunner(
        image=image_name,
        environment_variables={},
        volumes={f"{host_src_dir}": GUEST_RESULTS_DIR},
        devices=[],
        network="host",
        workdir=GUEST_SRC_DIR,
    )

    # bench_runner = DockerRunner(volumes={f"{host_src_dir}": GUEST_RESULTS_DIR})

    docker_runner |= gui_runner() | gpu_runner() | personal_runner()
    # docker_runner |= bench_runner

    comm = DockerCommLayer(docker_runner=docker_runner)
    platform = Platform(comm_layer=comm)
    return platform


def main():
    nb_runs = 1
    get_current_platform().comm.shell(
            command=["xhost +local:"],
            shell=True,
            current_dir="./",
            output_is_log=False,
    )

    platform = get_docker_platform()

    bench = GpuSchedulingBench(
        platform=platform,
        src_dir=GUEST_SRC_DIR,
        results_dir=GUEST_RESULTS_DIR,
    )

    bench2 = GpuSchedulingBench(
        platform=platform,
        src_dir=GUEST_SRC_DIR,
        results_dir=GUEST_RESULTS_DIR,
    )

    campaign = CampaignCartesianProduct(
        name="gpuscheduling",
        benchmark=bench,
        nb_runs=nb_runs,
        variables={
            "kernel_names": [("timer_spin", "timer_spin")],
            "cthread_counts": [(1024,1024)],
            "block_counts": [(14,14), (4,24)],
            "additional_infos": [(250000000,250000000)],
            "release_times": [(0,0)],
            "sm_masks": [("0xffffffffffffff80", "0xffffffffffffc07f"), ("0xfffffffffffffff0","0xffffffffffffc00f"), (None, None)],
            "data_sizes": [(0, 0)],
            "iterations": [1,2],
        },
        constants={},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    K = 1000
    M = K*K

    campaign2 = CampaignCartesianProduct(
        name="gpuscheduling",
        benchmark=bench2,
        nb_runs=nb_runs,
        variables={
            "kernel_names": [("vector_add", "vector_add")],
            "cthread_counts": [(1024,1024)],
            "block_counts": [(14,14)],
            "additional_infos": [(None,None)],
            "release_times": [(0,0)],
            "sm_masks": [(None, None), ("0xffffffffffffffe0","0xfffffffffffff01f"), ("0xffffffffffffff80", "0xffffffffffffc07f")],
            "data_sizes": [(200*M, 200*M), (100*M, 100*M)],
            "iterations": [1,2],
        },
        constants={},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    campaign_suite = CampaignSuite(campaigns=[
        campaign,
        campaign2,
    ])
    campaign_suite.run_suite()

    get_current_platform().comm.shell(
            command=["xhost -local:"],
            shell=True,
            current_dir="./",
            output_is_log=False,
    )

if __name__ == "__main__":
    main()
