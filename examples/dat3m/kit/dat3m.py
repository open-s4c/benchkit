# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pythainer.builders import (
    DockerBuilder,
    DockerfileDockerBuilder,
    UbuntuDockerBuilder,
)
from pythainer.builders.utils import project_git_clone
from pythainer.examples.builders import get_user_builder

from benchkit.utils.git import clone_repo


def vsyncer_builder() -> DockerBuilder:
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


def standalone_dat3m_builder() -> UbuntuDockerBuilder:
    work_dir = "/home/${USER_NAME}/workspace"

    builder = get_user_builder(
        image_name="dat3mbenchkit",
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
        commit="4.1.0",
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
    builder.env(
        name="OPTFLAGS",
        value='"-mem2reg -sroa -early-cse -indvars -loop-unroll -fix-irreducible -loop-simplify -simplifycfg -gvn"',
    )
    builder.space()

    builder.user()
    builder.workdir(path=f"{work_dir}/{dat3m_name}")

    builder.run(
        f'echo "java -jar dartagnan/target/dartagnan.jar cat/aarch64.cat --target=arm8 benchmarks/locks/ttas.c" > {dat3m_home}/run.sh'
    )  # TODO
    builder.run(f"chmod +x {dat3m_home}/run.sh")

    return builder
