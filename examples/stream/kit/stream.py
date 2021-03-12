# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for STREAM benchmark.
See: https://github.com/jeffhammond/STREAM.git
"""

import pathlib
from typing import Iterable, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType


class StreamBench(Benchmark):
    """Benchmark object for STREAM benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        platform: Platform | None = None,
        build_dir: PathType = None,
    ):
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            pre_run_hooks=pre_run_hooks,
            shared_libs=shared_libs,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform

        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path) and self.platform.comm.isfile(
            bench_src_path / "stream.c"
        ):
            raise ValueError(
                f"Invalid STREAM source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path.resolve()

        self._build_dir = self._bench_src_path / (
            f"build-{self.platform.hostname}" if build_dir is None else build_dir
        )

    @property
    def bench_src_path(self):
        return self._bench_src_path

    @staticmethod
    def get_build_var_names():
        return [
            "array_size",
        ]

    @staticmethod
    def get_run_var_names():
        return [
            "nb_threads",
            "master_thread_core",
        ]

    @staticmethod
    def get_tilt_var_names():
        return []

    def dependencies(self):
        return super().dependencies() + [
            PackageDependency("build-essential"),
        ]

    def build_tilt(self, **kwargs):
        raise NotImplementedError("Tilt is not necessary for this benchmark.")

    def prebuild_bench(self, **_kwargs):
        pass

    def build_bench(  # pylint: disable=arguments-differ
        self,
        array_size: int,
        **_kwargs,
    ):
        build_dir = self._build_dir

        self.platform.comm.shell(
            command=f"make N={array_size} BUILD={build_dir}",
            current_dir=self._bench_src_path,
        )

    def clean_bench(self):
        build_dir = self._build_dir

        self.platform.comm.shell(
            command=f"make clean BUILD={build_dir}",
            current_dir=self._bench_src_path,
        )

    def single_run(  # pylint: disable=arguments-differ
        self,
        master_thread_core: Optional[int],
        nb_threads: int,
        **_kwargs,
    ):
        environment = self._preload_env(master_thread_core=master_thread_core)
        if environment is None:
            environment = {}

        environment["OMP_NUM_THREADS"] = str(nb_threads)
        run_command = [
            "./stream_c.exe",
        ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            master_thread_core=master_thread_core,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._build_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        **_kwargs,
    ):
        output = command_output

        benchstats = output.split("Copy:")[-1].strip()
        copy = benchstats.split(" ")[0].strip()
        benchstats = output.split("Scale:")[-1].strip()
        scale = benchstats.split(" ")[0].strip()
        benchstats = output.split("Add:")[-1].strip()
        add = benchstats.split(" ")[0].strip()
        benchstats = output.split("Triad:")[-1].strip()
        triad = benchstats.split(" ")[0].strip()

        names = ["copy", "scale", "add", "triad"]
        values = [copy, scale, add, triad]
        result_dict = dict(zip(names, values))

        return result_dict


def stream_campaign(
    name: str,
    benchmark: Optional[StreamBench],
    src_dir: Optional[PathType],
    build_dir: Optional[str],
    results_dir: Optional[PathType],
    command_wrappers: Iterable[CommandWrapper],
    command_attachments: Iterable[CommandAttachment],
    shared_libs: Iterable[SharedLib],
    pre_run_hooks: Iterable[PreRunHook],
    post_run_hooks: Iterable[PostRunHook],
    platform: Platform | None = None,
    nb_runs: int = 1,
    array_size: Iterable[int] = (),
    master_thread_core: Iterable[int | None] = (),
    nb_threads: Iterable[int] = (1,),
    constants: Constants = None,
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the STREAM benchmark."""
    variables = {
        "array_size": array_size,
        "master_thread_core": master_thread_core,
        "nb_threads": nb_threads,
    }

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = StreamBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
            build_dir=build_dir,
        )

    return CampaignCartesianProduct(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        constants=constants,
        debug=debug,
        gdb=gdb,
        enable_data_dir=enable_data_dir,
        continuing=continuing,
        benchmark_duration_seconds=0,
        results_dir=results_dir,
    )
