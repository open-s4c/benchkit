# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
GPU-enabled pythainer container, exposed to benchkit as a platform.

Every command a benchmark runs through `ctx.exec` is executed inside a fresh
container of this image (`docker run --rm ...`): build artifacts and results
must therefore live on a mounted volume. The mounted directory is mapped at
the *same* absolute path inside the container, so host paths (build dir,
per-record data dirs) are valid on both sides without any translation.
"""

from pathlib import Path

from pythainer.builders import UbuntuDockerBuilder
from pythainer.examples.runners import gpu_runner
from pythainer.runners import ConcreteDockerRunner, DockerRunner

from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform

DEFAULT_IMAGE = "benchkit-gpu-tasksets"
CUDA_BASE_IMAGE = "nvidia/cuda:12.6.3-devel-ubuntu24.04"


def gpu_builder(image_name: str = DEFAULT_IMAGE) -> UbuntuDockerBuilder:
    """
    Describe the container image: CUDA toolchain plus a non-root user whose
    UID/GID match the host user, so files written in mounted volumes stay
    owned by the host user.

    Args:
        image_name (str): tag of the image to build.

    Returns:
        UbuntuDockerBuilder: the builder; call `.build()` to build the image.
    """
    builder = UbuntuDockerBuilder(tag=image_name, ubuntu_base_tag=CUDA_BASE_IMAGE)
    builder.space()

    builder.env(name="DEBIAN_FRONTEND", value="noninteractive")
    builder.add_packages(packages=["git", "sudo"])
    builder.space()

    builder.desc("Non-root user matching the host UID/GID")
    builder.create_user(username="user")
    builder.user()
    builder.workdir(path="/home/${USER_NAME}")
    builder.space()

    # The NVIDIA entrypoint prints a license banner on every `docker run`,
    # which would pollute the output of every command benchkit runs. The CUDA
    # toolchain is on PATH through ENV, so the entrypoint is not needed.
    builder.desc("No entrypoint: keep command outputs clean")
    builder.entrypoint(list_command=[])

    return builder


def gpu_platform(
    mount_dir: Path,
    image_name: str = DEFAULT_IMAGE,
) -> Platform:
    """
    Return a benchkit platform whose commands run inside the GPU container.

    Args:
        mount_dir (Path):
            host directory mounted at the same path inside the container; it
            must contain the sources, the build directory and the results.
        image_name (str): tag of the (already built) image to run.

    Returns:
        Platform: the platform to hand to the campaign.
    """
    mount_dir = Path(mount_dir).resolve()
    runner = ConcreteDockerRunner(
        image=image_name,
        workdir=mount_dir,
        tty=False,  # commands are run non-interactively by benchkit
    )
    runner |= gpu_runner() | DockerRunner(volumes={f"{mount_dir}": f"{mount_dir}"})
    return Platform(comm_layer=DockerCommLayer(docker_runner=runner))
