# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import sys
from typing import Tuple

from benchkit.platforms import Platform
from benchkit.sharedlibs import FromSourceSharedLib
from benchkit.utils.types import EnvironmentVariables, LdPreloadLibraries


def cmake_configure_build(
    platform: Platform,
    src_dir: pathlib.Path,
    build_dir: pathlib.Path,
    debug: bool,
    make_suffix: str,
) -> None:
    platform.comm.makedirs(path=build_dir, exist_ok=True)

    cmake_build_type = "Debug" if debug else "Release"
    platform.comm.shell(
        command=["cmake", f"-DCMAKE_BUILD_TYPE={cmake_build_type}", f"{src_dir}"],
        current_dir=build_dir,
        output_is_log=True,
    )
    platform.comm.shell(
        command=f"make{make_suffix}",
        current_dir=build_dir,
        output_is_log=True,
    )


class TiltLib(FromSourceSharedLib):
    def __init__(
        self,
        tilt_locks_dir: pathlib.Path,
        build_prefix: str = "build",
        debug_mode: bool = False,
    ) -> None:
        super().__init__(src_path=tilt_locks_dir, debug_mode=debug_mode)
        self.build_dir = self.src_path / f"{build_prefix}-{self.platform.hostname}"

    def build(self) -> None:
        cmake_configure_build(
            platform=self.platform,
            src_dir=self.src_path,
            build_dir=self.build_dir,
            debug=False,
            make_suffix=" -j1",
        )

    def preload(
        self,
        **kwargs,
    ) -> Tuple[LdPreloadLibraries, EnvironmentVariables]:
        ld_preloads, env_vars = super().preload(
            **kwargs,
        )

        lock = kwargs.get("lock")
        if lock:
            lib_lockname = f"lib{lock}"
            lib_path = (self.build_dir / f"{lib_lockname}.so").resolve()
            if lib_path.is_file():
                ld_preloads.append(str(lib_path))
            else:
                print(
                    f"[WARNING] Tilt lib lock with name {lib_lockname} not found (in {lib_path}), not enabling.",
                    file=sys.stderr,
                )

        return ld_preloads, env_vars
