# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
from typing import Any, Dict, Iterable, List

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType

# See below where variables are specified on why these variables are necessary
BUILD_VARIABLES = [
    "threading_implementation",
    "use_color_buffer_per_thread",
    "use_slim_bvh_nodes",
    "triangle_intersection_algo",
    "work_square_size",
    "aabb_hit_implementation",
    "bvh_first_hit_caching",
    "bvh_sah",
]
RUN_VARIABLES = ["nb_threads", "preset"]


class RayTracerBenchmark(Benchmark):
    """Benchmark object for main benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        bench_src_dir: PathType | None = None,
        copy_src_to_build: bool = False,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        self._src_dir = src_dir
        self._bench_src_path = bench_src_dir
        if platform is not None:
            self.platform = platform

        # If this is on a remote machine, copy the source to the remote machine
        if not copy_src_to_build:
            return

        # We need trailing slashes to make sure the directories are not copied in each other and
        # rather the files are synced between the directories
        src = pathlib.Path(self._src_dir)
        dst = pathlib.Path(self._bench_src_path)

        folders_to_copy = ["src", "include", "benchmarking/cornell"]

        files_to_copy = [
            "build.sh",
            "CMakeLists.txt",
            "custom_config.h",
            "benchmarking/suzanne_on_table.glb",
            "benchmarking/suzanne_on_table_hr.glb",
        ]

        # If you want to copy a folder, you need to append it with a leading / to make sure
        # that the contents are not copied and that the folders are not copied into each other.
        # Since pathlib does not support this (it auto strips trailing slashes), you have
        # to add them manually.
        for folder in folders_to_copy:
            self.platform.comm.copy_from_host(f"{src / folder}/", f"{dst / folder}/")

        for file in files_to_copy:
            self.platform.comm.copy_from_host(f"{src / file}", f"{dst / file}")

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return BUILD_VARIABLES

    @staticmethod
    def get_run_var_names() -> List[str]:
        return RUN_VARIABLES

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("cmake"),
        ]

    def prebuild_bench(self, **kwargs):
        pass

    def build_bench(self, **kwargs) -> None:
        # Create the config file that sets the build parameters
        custom_config = "#pragma once\n"
        for v in BUILD_VARIABLES:
            custom_config += f"#define {v.upper()} {kwargs.get(v)}\n"

        self.platform.comm.write_content_to_file(
            custom_config, pathlib.Path(self._bench_src_path) / "custom_config.h"
        )

        self.platform.comm.shell(
            command="./build.sh",
            current_dir=self._bench_src_path,
        )

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        record_data_dir: PathType,
        preset: str,
        nb_threads: int = 2,
        **kwargs,
    ) -> str:
        environment = self._preload_env(
            record_data_dir=record_data_dir,
            preset=preset,
            nb_threads=nb_threads,
            **kwargs,
        )

        run_command = [
            "./raytracer",
            "--threads",
            str(nb_threads),
            "--preset",
            preset,
            "--outfile",
            str(record_data_dir / "benchmark.bmp"),
        ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            record_data_dir=record_data_dir,
            preset=preset,
            nb_threads=nb_threads,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._bench_src_path,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
            record_data_dir=record_data_dir,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        nb_threads = int(run_variables["nb_threads"])
        try:
            duration = command_output.splitlines()[-1].split(": ")[1].split()[0]
        except ValueError:
            print(command_output)
            duration = "N/A"

        return {"nb_threads": nb_threads, "duration": duration}
