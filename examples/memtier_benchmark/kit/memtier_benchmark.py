# Copyright (C) 2025 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for the Redis benchmark.
See https://redis.io
"""

import pathlib
import time
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType


class MemtierBench(Benchmark):
    """
    Benchmark object for memtier_benchmark + redis version 7.2.4 benchmark.
    """

    def __init__(
        self,
        server_src_dir: PathType,
        client_src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        server_platform: Platform | None = None,
        client_platform: Platform | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )

        if server_platform is not None:
            self.server_platform = server_platform

        server_bench_src_path = pathlib.Path(server_src_dir)
        server_makefile_path = server_bench_src_path / "Makefile"

        server_dir_exists = self.server_platform.comm.isdir(server_bench_src_path)
        server_mkf_exists = self.server_platform.comm.isfile(server_makefile_path)
        if not (server_dir_exists and server_mkf_exists):
            raise ValueError(
                f"Invalid Redis source path: {server_bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._server_bench_src_path = server_bench_src_path
        self._server_bench_bin_path = self._server_bench_src_path / "src"

        if client_platform is not None:
            self.client_platform = client_platform

        client_bench_src_path = pathlib.Path(client_src_dir)
        client_bench_hdr_path = client_bench_src_path / "memtier_benchmark.h"

        client_dir_exists = self.client_platform.comm.isdir(client_bench_src_path)
        client_hdr_exists = self.client_platform.comm.isfile(client_bench_hdr_path)

        if not (client_dir_exists and client_hdr_exists):
            raise ValueError(
                f"Invalid memtier_benchmark source path: {client_bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._client_bench_src_path = client_bench_src_path
        self._client_bench_bin_path = self._client_bench_src_path

    @property
    def bench_src_path(self) -> str:
        return self._server_bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "benchmark_duration_seconds",
            "server_cpu_order",
            "benchmark_cpu_order",
            "server_ip",
            "server_port",
            "nb_threads",
            "nb_clients",
            "nb_connections",
            "pipeline",
            "ratio",
            "data_size",
            "key_pattern",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("autoconf"),
            PackageDependency("automake"),
            PackageDependency("libpcre3-dev"),
            PackageDependency("libevent-dev"),
            PackageDependency("pkg-config"),
            PackageDependency("zlib1g-dev"),
            PackageDependency("libssl-dev"),
            PackageDependency("automake"),
            PackageDependency("automake"),
        ]

    def build_tilt(self, **kwargs) -> None:
        raise NotImplementedError("Tilt is not necessary for this benchmark.")

    def prebuild_bench(
        self,
        **_kwargs,
    ) -> None:
        nb_cpus = self.platform.nb_cpus()

        # Prepare redis server

        self.server_platform.comm.shell(
            command="make clean",
            current_dir=self._server_bench_src_path,
        )

        self.server_platform.comm.shell(
            command=f'make -j{nb_cpus} REDIS_CFLAGS="-fcommon"',
            current_dir=self._server_bench_src_path,
        )

        # Prepare memtier_benchmark client

        self.client_platform.comm.shell(
            command="autoreconf -ivf",
            current_dir=self._client_bench_src_path,
        )

        self.client_platform.comm.shell(
            command="./configure",
            current_dir=self._client_bench_src_path,
        )

        self.client_platform.comm.shell(
            command="make clean",
            current_dir=self._client_bench_src_path,
        )

        self.client_platform.comm.shell(
            command=f"make -j{nb_cpus}",
            current_dir=self._client_bench_src_path,
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
        server_ip: str = "127.0.0.1",
        server_port: str = "6379",
        nb_threads: int = 8,
        nb_clients: int = 10,
        pipeline: int = 8,
        ratio: str = "1:10",
        data_size: int = 1024,
        key_pattern: str = "R:R",
        **kwargs,
    ) -> str:

        self.server_platform.comm.pipe_shell(
            "cat ../redis.conf | "
            f"sed -e 's/# io-threads 4/io-threads {nb_threads}/' "
            "> ../redis-benchkit.conf-tmp",
            current_dir=self._server_bench_bin_path,
        )

        self.server_platform.comm.pipe_shell(
            "cat ../redis-benchkit.conf-tmp | "
            "sed -e 's/daemonize no/daemonize yes/' "
            "> ../redis-benchkit.conf",
            current_dir=self._server_bench_bin_path,
        )

        self.server_platform.comm.pipe_shell(
            "cat ../redis-benchkit.conf | "
            f"sed -e 's/bind 127.0.0.1 -::1/bind {server_ip}/' "
            "> ../redis-benchkit.conf-tmp",
            current_dir=self._server_bench_bin_path,
        )

        self.server_platform.comm.pipe_shell(
            "cat ../redis-benchkit.conf-tmp | "
            "sed -e 's/protected-mode yes/protected-mode no/' "
            "> ../redis-benchkit.conf",
            current_dir=self._server_bench_bin_path,
        )

        self.server_platform.comm.pipe_shell(
            "cat ../redis-benchkit.conf | "
            "sed -e 's/# io-threads-do-reads no/io-threads-do-reads yes/' "
            "> ../redis-benchkit.conf-tmp",
            current_dir=self._server_bench_bin_path,
        )

        self.server_platform.comm.pipe_shell(
            "mv ../redis-benchkit.conf-tmp ../redis-benchkit.conf",
            current_dir=self._server_bench_bin_path,
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
            "./memtier_benchmark",
            f"--host={server_ip}",
            f"--port={server_port}",
            f"--threads={nb_threads}",
            f"--clients={nb_clients}",
            f"--pipeline={pipeline}",
            f"--ratio={ratio}",
            f"--data-size={data_size}",
            f"--key-pattern={key_pattern}",
            "--key-minimum=1",
            "--key-maximum=10000000",
            "--distinct-client-seed",
            "--rate-limiting=100",
            f"--test-time={benchmark_duration_seconds}",
            "--hide-histogram",
        ]

        wrapped_server_run_command, wrapped_server_environment = self._wrap_command(
            run_command=server_command,
            environment=server_environment,
            cpu_order=server_cpu_order,
            master_thread_core=None,
            nb_threads=nb_threads,
            **kwargs,
        )

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=benchmark_environment,
            cpu_order=benchmark_cpu_order,
            master_thread_core=None,
            nb_threads=nb_threads,
            **kwargs,
        )

        # TODO: Make this code look better
        self.platform = self.server_platform

        output = self.run_bench_command(
            run_command=server_command,
            wrapped_run_command=wrapped_server_run_command,
            current_dir=self._server_bench_bin_path,
            environment=server_environment,
            wrapped_environment=wrapped_server_environment,
            print_output=False,
        )

        time.sleep(10)

        # TODO: Make this code look better
        self.platform = self.client_platform

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._client_bench_bin_path,
            environment=benchmark_environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        self.server_platform.comm.shell(
            f"./redis-cli -h {server_ip} FLUSHALL",
            current_dir=self._server_bench_bin_path,
        )

        self.server_platform.comm.shell(
            f"./redis-cli -h {server_ip} SHUTDOWN",
            current_dir=self._server_bench_bin_path,
        )

        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        benchmark_duration_seconds: int,
        **kwargs,
    ) -> Dict[str, Any]:

        start_table = 0
        output_lines = command_output.splitlines()

        for i, line in enumerate(output_lines):
            if "---------" in line:
                start_table = i
                break

        fields = output_lines[start_table - 1].split()[1:4]
        sets = output_lines[start_table + 1].split()[1:4]
        gets = output_lines[start_table + 2].split()[1:4]
        # waits = output_lines[start_table + 3].split()[1:4]
        totals = output_lines[start_table + 4].split()[1:4]

        sets_dict = {"Sets " + fields[i]: sets[i] for i in range(0, len(fields))}
        gets_dict = {"Gets " + fields[i]: gets[i] for i in range(0, len(fields))}
        totals_dict = {"Totals " + fields[i]: totals[i] for i in range(0, len(fields))}

        res_dict = {}
        res_dict.update(sets_dict)
        res_dict.update(gets_dict)
        res_dict.update(totals_dict)

        res_dict["throughput"] = res_dict["Totals Ops/sec"]

        return res_dict


def memtier_campaign(
    name: str = "memtier_campaign",
    benchmark: Optional[MemtierBench] = None,
    server_src_dir: Optional[PathType] = None,
    client_src_dir: Optional[PathType] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    server_platform: Platform | None = None,
    client_platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    server_cpu_order: Iterable[CpuOrder] = (),
    benchmark_cpu_order: Iterable[CpuOrder] = (),
    server_ip: Iterable[str] = ("127.0.0.1",),
    server_port: Iterable[str] = ("6379",),
    nb_threads: Iterable[int] = (8,),
    nb_clients: Iterable[int] = (10,),
    pipeline: Iterable[int] = (8,),
    ratio: Iterable[str] = ("1:10",),
    data_size: Iterable[int] = (1024,),
    key_pattern: Iterable[str] = ("R:R",),
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
        "server_ip": server_ip,
        "server_port": server_port,
        "pipeline": pipeline,
        "ratio": ratio,
        "data_size": data_size,
        "key_pattern": key_pattern,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if server_src_dir is None or client_src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = MemtierBench(
            server_src_dir=server_src_dir,
            client_src_dir=client_src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            server_platform=server_platform,
            client_platform=client_platform,
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
