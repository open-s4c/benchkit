# Copyright (C) 2024 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for the Redis benchmark.
See https://redis.io
"""

import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType


class RedisBench(Benchmark):
    """
    Benchmark object for redis version 7.2.4 benchmark.
    """

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

        # TODO duplication with LevelDB & perhaps many more in the future.
        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path) and self.platform.comm.isfile(
            bench_src_path / "Makefile"
        ):
            raise ValueError(
                f"Invalid Redis source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path
        self._bench_bin_path = self._bench_src_path / "src"

    @property
    def bench_src_path(self) -> str:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "server_cpu_order",
            "benchmark_cpu_order",
            "nb_threads",
            "nb_requests",
            "nb_clients",
            "test_name",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("libhwloc-dev"),
        ]

    def build_tilt(self, **kwargs) -> None:
        raise NotImplementedError("Tilt is not necessary for this benchmark.")

    def prebuild_bench(
        self,
        **_kwargs,
    ) -> None:
        self.platform.comm.shell(
            command="make clean",
            current_dir=self.bench_src_path,
            print_input=True,
            print_output=True,
        )

        self.platform.comm.shell(
            command='make -j50 REDIS_CFLAGS="-fcommon"',
            current_dir=self.bench_src_path,
            print_input=True,
            print_output=True,
        )

    def build_bench(  # pylint: disable=arguments-differ
        self,
        **_kwargs,
    ) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        server_cpu_order: CpuOrder = None,
        benchmark_cpu_order: CpuOrder = None,
        nb_threads: int = 4,
        nb_requests: int = 1000000,
        nb_clients: int = 50,
        test_name: str = "SET",
        **kwargs,
    ) -> str:

        self.platform.comm.pipe_shell(
            "cat ../redis.conf | "
            f"sed -e 's/io-threads 4/io-threads {nb_threads}/' "
            "> ../redis-benchkit.conf-tmp",
            current_dir=self._bench_bin_path,
            shell=False,
        )

        self.platform.comm.pipe_shell(
            "cat ../redis-benchkit.conf-tmp | "
            "sed -e 's/daemonize no/daemonize yes/' "
            "> ../redis-benchkit.conf",
            current_dir=self._bench_bin_path,
            shell=False,
        )

        self.platform.comm.shell(
            "rm ../redis-benchkit.conf-tmp",
            current_dir=self._bench_bin_path,
            shell=False,
        )

        server_environment = self._preload_env(
            cpu_order=server_cpu_order,
            master_thread_core=None,
            **kwargs,
        )
        benchmark_environment = self._preload_env(
            cpu_order=benchmark_cpu_order,
            master_thread_core=None,
            **kwargs,
        )

        server_command = [
            "./redis-server",
            "../redis-benchkit.conf",
        ]

        run_command = [
            "./redis-benchmark",
            "-n",
            f"{nb_requests}",
            "-c",
            f"{nb_clients}",
            "--threads",
            f"{nb_threads}",
            "-q",
            "-t",
            test_name,
            "--csv",
        ]

        wrapped_server_run_command, wrapped_server_environment = self._wrap_command(
            run_command=server_command,
            environment=server_environment,
            cpu_order=server_cpu_order,
            master_thread_core=None,
            **kwargs,
        )
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=benchmark_environment,
            cpu_order=benchmark_cpu_order,
            master_thread_core=None,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=server_command,
            wrapped_run_command=wrapped_server_run_command,
            current_dir=self._bench_bin_path,
            environment=server_environment,
            wrapped_environment=wrapped_server_environment,
            print_output=False,
        )
        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._bench_bin_path,
            environment=benchmark_environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        self.platform.comm.shell(
            "./redis-cli SHUTDOWN",
            current_dir=self._bench_bin_path,
        )

        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        benchmark_duration_seconds: int,
        **kwargs,
    ) -> Dict[str, Any]:

        tmp = command_output.splitlines()[0].split(",")
        fields = [x[1:-1] for x in tmp]

        tmp = command_output.splitlines()[-1].split(",")
        values = [x[1:-1] for x in tmp]

        result_dict = {fields[i]: values[i] for i in range(1, len(fields))}

        return result_dict


def redis_campaign(
    name: str = "redis_campaign",
    benchmark: Optional[RedisBench] = None,
    src_dir: Optional[PathType] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    server_cpu_order: Iterable[CpuOrder] = (),
    benchmark_cpu_order: Iterable[CpuOrder] = (),
    nb_threads: Iterable[int] = (4,),
    nb_requests: Iterable[int] = (1000000,),
    nb_clients: Iterable[int] = (50,),
    test_name: Iterable[int] = ("SET", "GET"),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Optional[Dict[str, Any]] = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the Will-it-Scale benchmark."""

    variables = {
        "server_cpu_order": server_cpu_order,
        "benchmark_cpu_order": benchmark_cpu_order,
        "nb_threads": nb_threads,
        "nb_clients": nb_clients,
        "nb_requests": nb_requests,
        "test_name": test_name,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = RedisBench(
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
