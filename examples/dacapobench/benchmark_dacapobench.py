# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType

supported_bench_names = [
    "avrora",
    "batik",
    "biojava",
    "cassandra",
    "eclipse",
    "fop",
    "graphchi",
    "h2",
    "jme",
    "jython",
    "kafka",
    "luindex",
    "lusearch",
    "pmd",
    "spring",
    "sunflow",
    "tomcat",
    "tradebeans",
    "tradesoap",
    "xalan",
    "zxing",
]


class DacapobenchBench(Benchmark):
    """Benchmark object for dacapobench benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform | None = None,
        clean_in_between_different_benchmarks: bool = False,
        # build_dir: PathType | None = None,
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
        if not self.platform.comm.isdir(bench_src_path) and self.platform.comm.isfile(
            bench_src_path / "build.xml"
        ):
            raise ValueError(
                f"Invalid dacapobench source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path
        self.clean_in_between_different_benchmarks = clean_in_between_different_benchmarks

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            "bench_name",
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "bench_name",
            "size",
            "nb_threads",
        ]

    @staticmethod
    def _parse_results(
        output: str,
        bench_name: str,
        nb_threads: int,
    ) -> Dict[str, str]:
        duration = ""
        for line in output.split("\n"):

            output_exceptions = ["lusearch"]
            if bench_name in output_exceptions and line.startswith("===== DaCapo processed"):
                splits = line.split(" ")
                duration = splits[6]
            elif (
                bench_name not in output_exceptions
                and line.startswith("===== DaCapo")
                and "PASSED" in line
            ):
                splits = line.split(" ")
                duration = splits[6]

        return {"duration": duration}

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("openjdk-11-jdk"),
            PackageDependency("openjdk-8-jdk"),
            PackageDependency("build-essential"),
            PackageDependency("cmake"),
            PackageDependency("cvs"),
            PackageDependency("subversion"),
            PackageDependency("ant"),
            PackageDependency("nodejs"),
            PackageDependency("npm"),
        ]

    def prebuild_bench(self, **_kwargs) -> None:
        pass

    def build_bench(
        self,
        bench_name: str,
        **kwargs,
    ) -> None:
        if bench_name not in supported_bench_names:
            raise ValueError(
                f"Invalid bench_names for dacapobench: {bench_name}\n"
                f"The supported bench names are: {supported_bench_names}."
            )

        benchmark_cache_file = "benchmark_cache.txt"

        try:
            with open(benchmark_cache_file, "r", encoding="utf-8") as f:
                cached_benchmark = f.read()
        except FileNotFoundError:
            cached_benchmark = ""

        should_clean = self.clean_in_between_different_benchmarks and cached_benchmark != bench_name

        if should_clean:
            self.platform.comm.shell(
                command="ant clean",
                current_dir=self._bench_src_path,
                output_is_log=True,
            )
            if os.path.exists(benchmark_cache_file):
                os.remove(benchmark_cache_file)
            cached_benchmark = ""

        if cached_benchmark != bench_name:
            self.platform.comm.shell(
                command=f"ant {bench_name}",
                current_dir=self._bench_src_path,
                output_is_log=True,
            )
            with open(benchmark_cache_file, "w", encoding="utf-8") as f:
                f.write(bench_name)  # no newline added

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        size: str,
        nb_threads: int,
        bench_name: str,
        **kwargs,
    ) -> str:

        environment = self._preload_env(
            size=size,
            **kwargs,
        )

        run_command = [
            "java",
            "-jar",
            "dacapo-evaluation-git-4e3de06d.jar",
            bench_name,
            f"--thread-count={nb_threads}",
            f"--size={size}",
            "--iterations=1",
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
        **_kwargs,
    ) -> Dict[str, Any]:
        nb_threads = int(run_variables["nb_threads"])
        bench_name = run_variables["bench_name"]
        result_dict = self._parse_results(
            output=command_output, bench_name=bench_name, nb_threads=nb_threads
        )
        return result_dict


def dacapobench_campaign(
    name: str = "dacapobench_campaign",
    benchmark: Optional[DacapobenchBench] = None,
    bench_names: Iterable[str] = ("lusearch",),
    src_dir: Optional[PathType] = None,
    # build_dir: Optional[str] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    size: Iterable[str] = ("default",),
    nb_threads: Iterable[int] = (1,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    clean_in_between_different_benchmarks: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
    symlink_latest: bool = False,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the dacapobench benchmark."""
    variables = {
        "size": size,
        "nb_threads": nb_threads,
        "bench_name": bench_names,
    }
    if pretty is not None:
        pretty = {"size": pretty}

    if not all(bench_name in supported_bench_names for bench_name in bench_names):
        unsupported_benchmarks = [
            bench_name for bench_name in bench_names if bench_name not in supported_bench_names
        ]
        raise ValueError(
            f"Invalid bench_names for dacapobench: {unsupported_benchmarks}\n"
            f"The supported bench names are: {supported_bench_names}."
        )

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = DacapobenchBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            clean_in_between_different_benchmarks=clean_in_between_different_benchmarks,
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
        symlink_latest=symlink_latest,
    )
