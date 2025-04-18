# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pythainer.builders import PartialDockerBuilder, UbuntuDockerBuilder
from pythainer.examples.builders import get_user_gui_builder
from pythainer.examples.runners import gpu_runner, gui_runner, personal_runner
from pythainer.runners import ConcreteDockerRunner, DockerRunner

from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform
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


def get_gpu_builder(image_name: str) -> UbuntuDockerBuilder:
    builder = get_user_gui_builder(
        image_name=image_name,
        base_ubuntu_image="nvidia/cuda:12.2.0-devel-ubuntu22.04",
    )
    builder.space()

    remove_motd(builder=builder)

    builder.user()
    builder.workdir("/home/${USER_NAME}")

    return builder


def get_gpu_runner(
    workdir: PathType = "/home/user",
    image_name: str = "gpubenchkit",
) -> ConcreteDockerRunner:
    builder = get_gpu_builder(image_name=image_name)
    builder.build()

    runner = ConcreteDockerRunner(
        image=image_name,
        environment_variables={},
        devices=[],
        network="host",
        workdir=workdir,
    )

    runner |= gui_runner() | gpu_runner() | personal_runner()

    return runner


def get_gpu_docker_platform(
    host_src_dir: PathType,
    guest_src_dir: PathType,
    image_name: str = "gpubenchkit",
) -> Platform:
    docker_runner = get_gpu_runner(
        workdir=guest_src_dir,
        image_name=image_name,
    )
    bench_runner = DockerRunner(volumes={f"{host_src_dir}": f"{guest_src_dir}"})
    runner = docker_runner | bench_runner
    comm = DockerCommLayer(docker_runner=runner)
    platform = Platform(comm_layer=comm)
    return platform


if __name__ == "__main__":
    runner = get_gpu_runner(image_name="gpubenchkit")
    runner.run()
