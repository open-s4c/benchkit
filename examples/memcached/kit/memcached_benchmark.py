# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for the Memcached benchmark.
See https://memcached.org/
"""

import pathlib
import time
import sys
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType


class MemcachedBench(Benchmark):
    """
    Benchmark object for memcached benchmark.

    Uses memtier_benchmark repository.
    See https://github.com/RedisLabs/memtier_benchmark.git
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

        self._server_bench_src_path = pathlib.Path(server_src_dir)
        self._server_bench_bin_path = self._server_bench_src_path

        if client_platform is not None:
            self.client_platform = client_platform

        client_bench_src_path = pathlib.Path(client_src_dir)

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
            PackageDependency("libevent-dev"),
            PackageDependency("build-essential"),
            PackageDependency("pkg-config"),
            PackageDependency("automake"),
        ]

    def build_tilt(self, **kwargs) -> None:
        raise NotImplementedError("Tilt is not necessary for this benchmark.")

    def prebuild_bench(
        self,
        **_kwargs,
    ) -> None:
        nb_cpus = self.platform.nb_cpus()

        # Prepare memcached server

        self.server_platform.comm.shell(
            command="./autogen.sh",
            current_dir=self._server_bench_src_path,
        )

        # If it is a mac with lib-event installed with Brew (otherwise error on run)
        if sys.platform == "darwin":
            self.server_platform.comm.shell(
                command="./configure --with-libevent=/opt/homebrew/opt/libevent",
                current_dir=self._server_bench_src_path,
            )
        else:
            self.server_platform.comm.shell(
                command="./configure",
                current_dir=self._server_bench_src_path,
            )

        self.server_platform.comm.shell(
            command="make",
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
        server_port: str = "11211",
        nb_threads: int = 4,
        nb_clients: int = 10,
        pipeline: int = 1,
        ratio: str = "1:10",
        data_size: int = 1024,
        key_pattern: str = "R:R",
        **kwargs,
    ) -> str:
        server_command = [
            "./memcached",
            f"-l {server_ip}",
            f"-p {server_port}",
            f"-t {nb_threads}",
            f"-P memcached.pid",
            "-d",  # Run as daemon
        ]

        self.server_platform.comm.shell(
            command=server_command,
            current_dir=self._server_bench_bin_path,
        )

        benchmark_environment = self._preload_env(
            cpu_order=benchmark_cpu_order,
            master_thread_core=None,
            **kwargs,
        )

        run_command = [
            "./memtier_benchmark",
            f"--server={server_ip}",
            f"--port={server_port}",
            "--protocol=memcache_text",
            f"--threads={nb_threads}",
            f"--clients={nb_clients}",
            f"--pipeline={pipeline}",
            f"--ratio={ratio}",
            f"--data-size={data_size}",
            f"--key-pattern={key_pattern}",
            "--key-minimum=1",
            "--key-maximum=10000000",
            "--distinct-client-seed",
            f"--test-time={benchmark_duration_seconds}",
            "--hide-histogram",
        ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=benchmark_environment,
            cpu_order=benchmark_cpu_order,
            master_thread_core=None,
            nb_threads=nb_threads,
            **kwargs,
        )

        self.platform = self.client_platform

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._client_bench_bin_path,
            environment=benchmark_environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        self.server_platform.comm.shell("pkill memcached")
        time.sleep(2) # It can take some time to free the port after pkill

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
        # waits = output_lines[start_table + 3].split()[1:4] # Is this necessary? in th
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


def memcached_campaign(
    name: str = "memcached_campaign",
    benchmark: Optional[MemcachedBench] = None,
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
    server_port: Iterable[str] = ("11211",),
    nb_threads: Iterable[int] = (4,),
    nb_clients: Iterable[int] = (10,),
    pipeline: Iterable[int] = (1,),
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
    """Return a cartesian product campaign configured for Memcached with memtier_benchmark."""

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
        pass

    if benchmark is None:
        benchmark = MemcachedBench(
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
