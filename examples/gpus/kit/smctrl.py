# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pythainer.builders import DockerBuilder
from pythainer.builders.utils import project_git_clone


def install_libsmctrl_from_src(
    builder: DockerBuilder,
    workdir: str,
    smctrl_commit: str = "72ba87e277572eddb25784563faa3eac111c9556",
    debug=True,
) -> None:
    builder.desc("Install libsmctrl from source")
    project_git_clone(
        builder=builder,
        workdir=workdir,
        git_url="http://rtsrv.cs.unc.edu/cgit/cgit.cgi/libsmctrl.git",
        commit=smctrl_commit,
        single_run_command=True,
    )
    flags = ' CFLAGS="-g -O0"' if debug else ""
    builder.run_multiple(
        commands=[
            f"cd {workdir}/libsmctrl",
            f'make -j$(nproc) NVCC=$(which nvcc){flags} libsmctrl.a',
        ],
    )
    builder.space()
