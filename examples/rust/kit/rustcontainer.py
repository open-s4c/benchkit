# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pythainer.examples.builders import get_user_builder, rust_builder
from pythainer.runners import ConcreteDockerRunner, DockerRunner

from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform
from benchkit.utils.types import PathType


def get_local_docker_platform(docker_runner: ConcreteDockerRunner) -> Platform:
    docker_comm = DockerCommLayer(docker_runner=docker_runner)
    platform = Platform(comm_layer=docker_comm)
    return platform


def get_rust_docker_runner(host_dir: PathType) -> ConcreteDockerRunner:
    guest_ws_dir = "/home/user/workspace"
    guest_mount_dir = f"{guest_ws_dir}/mnt"

    builder = get_user_builder(
        image_name="rustcont",
        base_ubuntu_image="ubuntu:22.04",
    )
    builder.space()

    builder.user()
    builder.workdir(path=guest_ws_dir)
    builder |= rust_builder()
    builder.space()

    builder.build()
    volume_runner = DockerRunner(volumes={f"{host_dir}": f"{guest_mount_dir}"})
    runner = builder.get_runner() | volume_runner

    return runner


def get_rust_docker_platform(host_dir: PathType) -> Platform:
    runner = get_rust_docker_runner(host_dir=host_dir)
    platform = get_local_docker_platform(docker_runner=runner)
    return platform
