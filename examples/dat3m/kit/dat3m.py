# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pythainer.builders import UbuntuDockerBuilder
from pythainer.builders.utils import project_git_clone
from pythainer.examples.builders import get_user_builder
from pythainer.runners import ConcreteDockerRunner
from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform


_DEFAULT_DAT3M_VERSION = "4.1.0"


def standalone_dat3m_builder(
    version_acronym: str = "",
    dat3m_commit: str = _DEFAULT_DAT3M_VERSION,
) -> UbuntuDockerBuilder:
    work_dir = "/home/${USER_NAME}/workspace"

    suffix = f"-{version_acronym}" if version_acronym else ""
    image_name = f"dat3mbenchkit{suffix}"

    builder = get_user_builder(
        image_name=image_name,
        base_ubuntu_image="ubuntu:22.04",
        user_name="tony",
        packages=[
            "build-essential",
            "clang",
            "git",
            "graphviz",
            "llvm",
            "maven",
            "openjdk-17-jdk",
            "openjdk-17-jre",
            "wget",
        ],
    )
    builder.space()

    builder.desc("Install Dat3M from source")
    dat3m_name = project_git_clone(
        builder=builder,
        workdir=work_dir,
        git_url="https://github.com/hernanponcedeleon/Dat3M.git",
        commit=dat3m_commit,
        single_run_command=True,
    )
    dat3m_home = f"{work_dir}/{dat3m_name}"
    builder.run_multiple(
        commands=[
            f"cd {dat3m_home}",
            "mvn clean install -DskipTests",
        ]
    )
    builder.space()

    builder.desc("Prepare environment")
    builder.root()
    builder.env(name="DAT3M_HOME", value=dat3m_home)
    builder.env(name="DAT3M_OUTPUT", value=f"{work_dir}/output")
    builder.env(name="CFLAGS", value='"-I$DAT3M_HOME/include"')
    optflags_lst = [
        "-mem2reg",
        "-sroa",
        "-early-cse",
        "-indvars",
        "-loop-unroll",
        "-fix-irreducible",
        "-loop-simplify",
        "-simplifycfg",
        "-gvn",
    ]
    optflags_str = " ".join(optflags_lst)
    builder.env(
        name="OPTFLAGS",
        value=f'"{optflags_str}"',
    )
    builder.space()

    builder.user()
    builder.workdir(path=f"{work_dir}/{dat3m_name}")

    return builder


def get_local_docker_platform(docker_runner: ConcreteDockerRunner) -> Platform:
    docker_comm = DockerCommLayer(docker_runner=docker_runner)
    platform = Platform(comm_layer=docker_comm)
    return platform


def get_dat3m_docker_platform(
    version_acronym: str = "",
    dat3m_commit: str = _DEFAULT_DAT3M_VERSION,
) -> Platform:
    dat3m_builder = standalone_dat3m_builder(
        version_acronym=version_acronym,
        dat3m_commit=dat3m_commit,
    )
    # TODO building images does not support yet remote, the plan would be to give an optional
    #  shell_out callback to that build() function and provide with the platform.shell from the
    #  selected host.
    dat3m_builder.build()
    dar3m_runner = dat3m_builder.get_runner()
    platform = get_local_docker_platform(docker_runner=dar3m_runner)
    return platform
