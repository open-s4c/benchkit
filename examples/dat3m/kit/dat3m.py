# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pythainer.builders import UbuntuDockerBuilder
from pythainer.builders.utils import project_git_clone
from pythainer.examples.builders import get_user_builder


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
