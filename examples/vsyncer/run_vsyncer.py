#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from vsyncer import vsyncer_builder

from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform


def get_vsyncer_docker_platform() -> Platform:
    builder = vsyncer_builder()
    builder.build()
    runner = builder.get_runner()
    comm_layer = DockerCommLayer(docker_runner=runner)
    platform = Platform(comm_layer=comm_layer)
    return platform


def main():
    platform = get_vsyncer_docker_platform()
    platform.comm.shell(command="vsyncer version")


if __name__ == "__main__":
    main()
