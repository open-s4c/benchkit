#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Benchkit support for Volano
"""

import subprocess
import time
import os
import re
import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType


class CounterBenchmark(Benchmark):
    """Benchmark object for VOLANO benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        platform: Platform | None = None,
        build_dir: PathType | None = None,
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
            bench_src_path / "benchmarks/volano_bench.cc"
        ):
            raise ValueError(
                f"Invalid Counter source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path

        if build_dir is None:
            self._build_dir = self._bench_src_path / f"build-{self.platform.hostname}"
            self._tmpdb_dir = "/tmp/benchkit_volano"
        else:
            self._build_dir = self._bench_src_path / build_dir
            self._tmpdb_dir = self._build_dir / "tmp" / "benchkit_volano"

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "start",  # starting room (1)
            "rooms",  # number of rooms (50)
            "users",  # number of users per room (20)
            "count",  # messages per user or 0 for no limit (100)
            "pause",  # message pause in second or 0 for  pacing (0)
            "host",   # server host name (localhost)
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    @staticmethod
    def _parse_results(
        output: str,
    ) -> Dict[str, Any]:
        # Use regular expression to find the average throughput
        match = re.search(r'Average throughput\s*=\s*(\d+)\s*messages per second', output)
        if match:
            average_throughput = int(match.group(1))
            print(f'Average throughput: {average_throughput} messages per second')
            result_dict = {"average_throughput": average_throughput}
            print(result_dict)
        else:
            raise ValueError('Average throughput not found')

        return result_dict

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("java")
        ]

    def build_tilt(self, **kwargs) -> None:
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs) -> None:
        build_dir = self._build_dir
        self.platform.comm.makedirs(path=build_dir, exist_ok=True)

        if not self.platform.comm.isdir(self._tmpdb_dir):
            self.platform.comm.makedirs(path=self._tmpdb_dir, exist_ok=True)

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        start: int = 1,
        rooms: int = 50,
        users: int = 20,
        count: int = 101,
        pause: int = 0,
        host: str = "localhost",
        **kwargs,
    ) -> str:
        environment = self._preload_env(
            start=start,
            rooms=rooms,
            users=users,
            count=count,
            pause=pause,
            host=host,
            **kwargs,
        )

        run_command = [
            "java",
            "-cp",
            "deps/lib/volano-chat-server.jar",
            "COM.volano.Mark",
            "-run",
            "-start",
            f"{start}",
            "-rooms",
            f"{rooms}",
            "-users",
            f"{users}",
            "-count",
            f"{count}",
            "-pause",
            f"{pause}",
            "-host",
            f"{host}"
        ]
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            environment=environment,
            wrapped_environment=wrapped_environment,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._build_dir,
            print_output=True,
        )

        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = self._parse_results(output=command_output)
        return result_dict


def counter_campaign(
    name: str = "volano_campaign",
    benchmark: Optional[CounterBenchmark] = None,
    src_dir: Optional[PathType] = "./",
    build_dir: Optional[str] = "./",
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 2,
    benchmark_duration_seconds: int = 5,
    start: Iterable[int] = (1, ),
    rooms: Iterable[int] = (20, 25, 30, 35, 40, 45, 50, 55, 60),
    users: Iterable[int] = (20, ),
    count: Iterable[int] = (100, ),
    pause: Iterable[int] = (0, ),
    host: Iterable[str] = ("localhost", ),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = True,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the VOLANO benchmark."""
    variables = {
        "start": start,
        "rooms": rooms,
        "users": users,
        "count": count,
        "pause": pause,
        "host": host,
    }

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = CounterBenchmark(
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
        benchmark_duration_seconds=benchmark_duration_seconds,
        results_dir=results_dir,
        pretty=pretty,
    )


def main():
    # Define the command to be executed
    command = "./startup.sh server loop openjdk"

    # Define the directory where the command should be executed
    working_directory = os.path.join(os.getcwd(), "deps")

    # Ensure the directory exists
    if not os.path.isdir(working_directory):
        raise FileNotFoundError(f"The directory {working_directory} does not exist")

    process = subprocess.Popen(
        command,
        shell=True,
        cwd=working_directory,
    )

    print(f"Started volano server process with PID: {process.pid}")

    # Example: Wait for 10 seconds before terminating the process
    time.sleep(5)
    print("start bench")
    campaign = counter_campaign(
        post_run_hooks=[],
        command_wrappers=[],
        src_dir="./",
        build_dir="./",
    )
    campaign.run()

    process.terminate()

    campaign.generate_graph(
        plot_name="barplot",
        x="rooms",
        y="average_throughput",
    )


if __name__ == "__main__":
    main()
