#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pythainer.builders import PartialDockerBuilder, UbuntuDockerBuilder
from pythainer.examples.builders import get_user_gui_builder
from pythainer.examples.installs import nsight_systems_install
from pythainer.examples.runners import gpu_runner, gui_runner, personal_runner
from pythainer.runners import ConcreteDockerRunner, DockerRunner
from smctrl import install_libsmctrl_from_src

from benchkit.commandwrappers.perf import enable_non_sudo_perf
from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform, get_current_platform
from benchkit.utils.dir import caller_dir
from benchkit.utils.types import PathType


def remove_motd(builder: PartialDockerBuilder) -> None:
    builder.root()
    builder.desc("Remove annoying motd")
    builder.run(
        command=(
            r"find /opt/nvidia/entrypoint.d/ "
            r'\( -name "*.txt" -o -name "10-banner.sh" -o -name "12-banner.sh" \) '
            r"-exec rm {} +"
        )
    )
    builder.space()


def get_gpu_builder(
    image_name: str = "gpubenchkit",
) -> UbuntuDockerBuilder:
    builder = get_user_gui_builder(
        image_name=image_name,
        base_ubuntu_image="nvidia/cuda:12.2.0-devel-ubuntu22.04",
    )
    builder.space()

    builder.root()
    nsight_systems_install(builder=builder)
    builder.user()
    builder.space()

    install_libsmctrl_from_src(
        builder=builder,
        workdir="/home/${USER_NAME}/workspace/libraries",
    )
    builder.space()

    remove_motd(builder=builder)

    builder.user()
    builder.workdir("/home/${USER_NAME}")
    builder.space()

    return builder


def get_gpu_runner(
    workdir: PathType = "/home/user",
    image_name: str = "gpubenchkit",
) -> ConcreteDockerRunner:
    runner = ConcreteDockerRunner(
        image=image_name,
        environment_variables={},
        devices=[],
        network="host",
        workdir=workdir,
    )
    runner |= gui_runner() | gpu_runner() | personal_runner()
    return runner


def get_gpu_docker_platform_from(
    runner: ConcreteDockerRunner,
    host_src_dir: PathType,
    guest_src_dir: PathType,
) -> Platform:
    bench_runner = DockerRunner(volumes={f"{host_src_dir}": f"{guest_src_dir}"})
    runner |= bench_runner
    comm = DockerCommLayer(docker_runner=runner)
    platform = Platform(comm_layer=comm)
    return platform


def get_gpu_docker_platform(
    host_src_dir: PathType,
    guest_src_dir: PathType,
    image_name: str = "gpubenchkit",
) -> Platform:
    builder = get_gpu_builder()
    builder.build()

    runner = get_gpu_runner(
        workdir=guest_src_dir,
        image_name=image_name,
    )

    platform = get_gpu_docker_platform_from(
        runner=runner,
        host_src_dir=host_src_dir,
        guest_src_dir=guest_src_dir,
    )

    return platform


def get_docker_runner() -> ConcreteDockerRunner:
    host_dir = caller_dir().parent.resolve()
    guest_dir = "/home/user/gpus"

    runner = get_gpu_runner(workdir=guest_dir)
    runner |= DockerRunner(volumes={f"{host_dir}": guest_dir})
    return runner


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    builder = get_gpu_builder()

    builder.build()

    runner = get_docker_runner()
    runner.run()


if __name__ == "__main__":
    main()
