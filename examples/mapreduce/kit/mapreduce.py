#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Benchkit support for Metis/MapReduce benchmark.
See: https://github.com/ydmao/Metis
"""

import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType


class MapReduceBench(Benchmark):
    """Benchmark object for Metis/MapReduce benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        platform: Platform | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform

        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path):
            raise ValueError(
                f"Invalid Metis source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )

        self._bench_src_path = bench_src_path

        # Build dir is automatically picked by Metis
        # = bench_src_path / out

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            # "memory_allocator",
            "sorting_algorithm",
            "data_structure",
            "mode",
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "bench_name",
            "nb_threads",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    @staticmethod
    def _parse_results(
        output: str,
        nb_threads: int,
        configuration_params: List[str],
        configuration_params_values: List[str],
    ) -> Dict[str, str]:
        runtime_line = next(
            line for line in output.split("\n") if line.strip().startswith("Sample")
        )

        # Extract all numbers from this line
        numbers = re.findall(r"\d+", runtime_line)
        values = list(map(int, numbers)) + [nb_threads] + configuration_params_values

        names = [
            "sample_ms",
            "map_ms",
            "reduce_ms",
            "merge_ms",
            "sum_ms",
            "real_ms",
            "nb_threads",
        ] + configuration_params

        result_dict = dict(zip(names, values))

        return result_dict

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("make"),
            PackageDependency("gcc"),
        ]

    def build_tilt(self, **kwargs) -> None:
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs) -> None:
        pass

    def build_bench(
        self,
        # memory_allocator: str,
        data_structure: str,
        sorting_algorithm: str,
        mode: str,
        **kwargs,
    ) -> None:
        src_dir = self._bench_src_path

        self.platform.comm.shell(
            command=[
                "./configure",
                f"--enable-map-ds={data_structure}",
                f"--enable-mode={mode}",
                f"--enable-sort={sorting_algorithm}",
                # f" --with-malloc={memory_allocator}",
            ],
            current_dir=src_dir,
            output_is_log=True,
        )

        # Build benchmarking files to src_dir/out
        self.platform.comm.shell(
            command="make",
            current_dir=src_dir,
            output_is_log=True,
        )

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        nb_threads: int = 2,
        bench_name: str = "",
        **kwargs,
    ) -> str:
        environment = self._preload_env(
            **kwargs,
        )

        # Use the same parameters mentioned in the Metis test suite
        # These are benchmark specific
        bench_params = []
        if bench_name == "wrmem":
            bench_params = []
        elif bench_name == "kmeans":
            bench_params = ["10", "16", "5000000", "40"]
        elif bench_name == "pca":
            bench_params = ["-R 2048", "-C 2048"]
        elif bench_name == "matrix_mult":
            bench_params = ["-l 2048", "-l 100"]

        run_command = [
            "./obj/" + bench_name,
            *bench_params,
            f"-p {nb_threads}",
        ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._bench_src_path,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        build_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        nb_threads = int(run_variables["nb_threads"])

        configuration_params = [
            # "memory_allocator",
            "sorting_algorithm",
            "data_structure",
            "mode",
        ]

        configuration_params_values = [
            # build_variables["memory_allocator"],
            build_variables["sorting_algorithm"],
            build_variables["data_structure"],
            build_variables["mode"],
        ]

        result_dict = self._parse_results(
            output=command_output,
            nb_threads=nb_threads,
            configuration_params=configuration_params,
            configuration_params_values=configuration_params_values,
        )

        return result_dict


def metis_campaign(
    name: str = "metis_campaign",
    benchmark: Optional[MapReduceBench] = None,
    bench_name: Iterable[str] = ("wrmem", "pca", "matrix_mult"),  # , "kmeans"
    src_dir: Optional[PathType] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    data_structure: Iterable[str] = ("btree", "array", "append"),
    sorting_algorithm: Iterable[str] = ("psrs", "mergesort"),
    mode: Iterable[str] = (
        "metis",
        "single_btree",
        "single_append-group_first",
        "single_append-merge_first",
    ),
    benchmark_duration_seconds: int = 5,
    nb_threads: Iterable[int] = (1, 2, 4, 8),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the MapReduce benchmark."""

    # Memory allocated could also be a variable [COULD NOT BE TESTED]
    # To use: Add here, in constructor and uncomment all comments
    # memory_allocator: Iterable[str] = ("malloc","flow","jemalloc"),
    variables = {
        "nb_threads": nb_threads,
        "bench_name": bench_name,
        "sorting_algorithm": sorting_algorithm,
        "data_structure": data_structure,
        "mode": mode,
    }

    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass

    if benchmark is None:
        benchmark = MapReduceBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
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
        benchmark_duration_seconds=benchmark_duration_seconds,
        results_dir=results_dir,
        pretty=pretty,
    )


if __name__ == "__main__":
    campaign = metis_campaign(
        post_run_hooks=[],
        command_wrappers=[],
        src_dir="./Metis/",
    )
    campaign.run()
