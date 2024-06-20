# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pythainer.builders import DockerfileDockerBuilder

from benchkit.utils.git import clone_repo


def vsyncer_builder() -> DockerfileDockerBuilder:
    clone_repo(
        repo_url="https://github.com/open-s4c/vsyncer.git",
        repo_src_dir="/tmp/vsyncer",
        commit="2a040dc00d03a806aeb07aeb2489b89eb33d59ff",
    )
    builder = DockerfileDockerBuilder(
        tag="pyvsyncer",
        dockerfile_path="/tmp/vsyncer/Dockerfile",
        build_dir="/tmp/vsyncer",
        use_uid_gid=False,
    )
    return builder
