# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import sys
from typing import Any, Dict, Iterable, List, Tuple

from benchkit.benchmark import Benchmark, SharedLib
from benchkit.platforms import Platform
from benchkit.sharedlibs import FromSourceSharedLib
from benchkit.utils.types import EnvironmentVariables, LdPreloadLibraries, PathType


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
                    (
                        f"[WARNING] Tilt lib lock with name {lib_lockname} not found "
                        f"(in '{lib_path}'), not enabling."
                    ),
                    file=sys.stderr,
                )

        return ld_preloads, env_vars


class SimpleMutexTestBench(Benchmark):
    def __init__(
        self,
        src_dir: PathType,
        shared_libs: Iterable[SharedLib] = (),
        platform: Platform = None,
    ) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=shared_libs,
            pre_run_hooks=(),
            post_run_hooks=(),
        )
        if platform is not None:
            self.platform = platform
        self._src_dir = src_dir.resolve()
        self._build_dir = self._src_dir / f"build-{self.platform.hostname}"

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._src_dir

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return ["lock"]

    def clean_bench(self) -> None:
        pass

    def prebuild_bench(
        self,
        **kwargs,
    ) -> int:
        cmake_configure_build(
            platform=self.platform,
            src_dir=self.bench_src_path,
            build_dir=self._build_dir,
            debug=self.must_debug(),
            make_suffix=self._parallel_make_str(),
        )
        return 0

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        pass

    def single_run(
        self,
        **kwargs,
    ) -> str:
        current_dir = self._build_dir
        environment = self._preload_env(
            **kwargs,
        )

        run_command = ["./mutex"]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=current_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
            ignore_ret_codes=(1,),
        )
        print(output)
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}
        return result_dict
