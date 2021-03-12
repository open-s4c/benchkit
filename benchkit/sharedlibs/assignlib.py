# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Share library enabling automatic thread to CPU assignment.
Several policies can be used, through defining environment variables.
"""

import os
from typing import Iterable, Optional, Tuple

from benchkit.sharedlibs import (
    EnvironmentVariables,
    FromSourceSharedLib,
    LdPreloadLibraries,
)
from benchkit.shell.shell import shell_out
from benchkit.utils.dir import (
    caller_file_abs_path,
    find_dependency_path,
    finddir_in_paths,
    gitrootdir,
)
from benchkit.utils.types import CpuOrder, PathType


class AssignLib(FromSourceSharedLib):
    """
    The assignment shared library. It requires the path to the source of interceptor.
    Whether to assign the main thread (first one to be created once starting the process) and what
    is the first thread to assign are parameters to the constructor.
    """

    def __init__(
        self,
        path: PathType,
        interceptor_path: PathType,
        assign_main_thread: bool = False,
        first_thread_to_assign: Optional[int] = None,
        debug_mode: bool = False,
    ):
        super().__init__(src_path=path, debug_mode=debug_mode)

        self.interceptor_path = interceptor_path
        so_path = self.build_dir / "src/libassign.so"
        self.so_path = so_path.resolve()
        self._assign_main_thread = assign_main_thread
        self.first_thread_to_assign = first_thread_to_assign

    @staticmethod
    def _environment(
        main_thread_cpu: Optional[int],
        worker_threads_cpu_order: Optional[Iterable[int]],
        first_thread_to_assign: Optional[int],
    ) -> EnvironmentVariables:
        env_vars = {}

        if main_thread_cpu is not None:
            env_vars["ASSIGN_CPU_MAIN_THREAD"] = str(main_thread_cpu)

        if worker_threads_cpu_order is not None:
            worker_threads_cpu_order_str = ",".join(map(str, worker_threads_cpu_order))
            env_vars["ASSIGN_CPU_WORKER_THREADS"] = worker_threads_cpu_order_str

        if first_thread_to_assign is not None:
            env_vars["ASSIGN_FIRST_THREAD"] = str(first_thread_to_assign)

        return env_vars

    def configure(self) -> None:
        super().configure()

        self._build()  # does not require any variable, can be built directly

    def preload(  # pylint: disable=arguments-differ
        self,
        cpu_order: CpuOrder,
        master_thread_core: Optional[int],
        **kwargs,
    ) -> Tuple[LdPreloadLibraries, EnvironmentVariables]:
        ld_preloads, other_env_vars = super().preload(
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            **kwargs,
        )

        main_thread_cpu = master_thread_core if self._assign_main_thread else None
        worker_threads_cpu_order = (
            self.platform.cpu_order(provided_order=cpu_order) if cpu_order is not None else None
        )

        libassign_env = self._environment(
            main_thread_cpu=main_thread_cpu,
            worker_threads_cpu_order=worker_threads_cpu_order,
            first_thread_to_assign=self.first_thread_to_assign,
        )

        ld_preloads.append(self.so_path)
        other_env_vars.update(libassign_env)

        return ld_preloads, other_env_vars

    def _build(self) -> None:
        os.makedirs(self.build_dir, exist_ok=True)
        cmake_build_type = "Debug" if self.must_debug() else "Release"
        shell_out(
            [
                "cmake",
                f"-DCMAKE_BUILD_TYPE={cmake_build_type}",
                f"-DCPM_interceptor_SOURCE={self.interceptor_path}",
                f"{self.src_path}",
            ],
            current_dir=self.build_dir,
        )
        shell_out("make assign", current_dir=self.build_dir)


def get_assignlib(
    assign_main_thread: bool,
    debug_mode: bool,
    first_thread_to_assign: Optional[int] = None,
) -> AssignLib:
    """
    Get an instance of the assign library.

    Args:
        assign_main_thread (bool):
            whether to assign the main thread with the assign lib. Can be disabled to use taskset
            instead.
        debug_mode (bool):
            whether to build the assign library with debug mode enabled.
        first_thread_to_assign (Optional[int], optional):
            how many threads to skip assigning before starting the assignment. Defaults to None.

    Returns:
        AssignLib: the assign library configured as per the arguments.
    """
    script_src_path = caller_file_abs_path()

    deps_path = find_dependency_path(script_src_path=script_src_path)
    repo_dir = gitrootdir(path=script_src_path)
    search_paths = [deps_path, repo_dir]

    sotools_path = finddir_in_paths(src_paths=search_paths, dir_name="sotools")
    interceptor_path = finddir_in_paths(src_paths=search_paths, dir_name="interceptor")

    return AssignLib(
        path=sotools_path,
        interceptor_path=interceptor_path,
        assign_main_thread=assign_main_thread,
        first_thread_to_assign=first_thread_to_assign,
        debug_mode=debug_mode,
    )
