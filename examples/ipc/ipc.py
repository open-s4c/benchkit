#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import re
from enum import Enum
from typing import Any, Dict, Iterable, List

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import Campaign, CampaignIterateVariables, CampaignSuite
from benchkit.commandwrappers import CommandWrapper
from benchkit.platforms import Platform, get_current_platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.dir import caller_dir
from benchkit.utils.types import PathType

BUILD_VARIABLES = []
RUN_VARIABLES = ["m"]
TILT_VARIABELS = []


class Target(Enum):
    LOCAL = 1
    HARMONY = 2
    ANDROID = 3
    CONTAINER = 4

    def is_mobile(self):
        return self == Target.HARMONY or self == Target.ANDROID


class IPCBenchmark(Benchmark):
    def __init__(
        self,
        bench_dir: PathType,
        target: Target = Target.LOCAL,
        skip_rebuild: bool = False,
        command_wrappers: Iterable[CommandWrapper] = [],
        command_attachments: Iterable[CommandAttachment] = [],
        shared_libs: Iterable[SharedLib] = [],
        pre_run_hooks: Iterable[PreRunHook] = [],
        post_run_hooks: Iterable[PostRunHook] = [],
        platform: Platform | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            
        )
        self.target = target
        self.bench_dir = bench_dir
        self.skip_rebuild = skip_rebuild

        if platform is not None:
            self.platform = platform

    @property
    def bench_src_path(self) -> pathlib.Path:
        return pathlib.Path(self.bench_dir)

    @staticmethod
    def get_build_var_names() -> List[str]:
        return BUILD_VARIABLES

    @staticmethod
    def get_run_var_names() -> List[str]:
        return RUN_VARIABLES

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return TILT_VARIABELS

    def parse_output_to_results(
        self,
        command_output: str,
        build_variables: Dict[str, Any],
        run_variables: Dict[str, Any],
        benchmark_duration_seconds: int,
        record_data_dir: PathType,
        **kwargs,
    ) -> Dict[str, Any]:
        raw_output = command_output[command_output.index("Successfully roundtrip") :]
        m = re.search(pattern=r"took:\s*([\d.]+)s", string=raw_output)
        if m is None:
            raise ValueError(f"Failed to parse output: '{raw_output}'")
        time_value = m.group(1)
        parsed = {
            "time_seconds": time_value,
        }
        return parsed

    def build_bench(self, **kwargs) -> None:
        if self.target.is_mobile():
            return
        
        self.platform.comm.shell(
            command="cargo build",
            current_dir=self.bench_dir,
            output_is_log=True,
        )

    def clean_bench(self) -> None:
        if self.target.is_mobile():
            # TODO: remove copied file
            return

        if not self.skip_rebuild:
            self.platform.comm.shell(
                command="cargo clean",
                current_dir=self.bench_dir,
                output_is_log=True,
            )

    def single_run(self, m: int, **kwargs) -> str:
        run_command: List[str]
        output: str

        if self.target.is_mobile():
            run_command = ["./ipc_runner", "-m", f"{m}"]
        else: 
            run_command = ["cargo", "run", "--", "-m", f"{m}"]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment={},
            **kwargs,
        )

        output = self.run_bench_command(
            environment={},
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self.bench_dir,
            wrapped_environment=wrapped_environment,
            print_output=True,
        )

        return output


def main() -> None:
    nb_runs = 2
    variables = [{"m": 10**i} for i in range(1, 4)]
    skip_rebuild = True
    target = Target.ANDROID

    bench_dir: pathlib.Path | str = caller_dir() / "ipc_runner"
    platform: Platform | None = None

    this_dir = caller_dir()

    match target:
        case Target.LOCAL:
            platform = get_current_platform()
        case Target.HARMONY:
            from benchkit.devices.hdc import OpenHarmonyCommLayer, OpenHarmonyDeviceConnector
            
            bench_dir = "/data/testing/ipc/ipc_runner"
            device = list(OpenHarmonyDeviceConnector.query_devices())[0]
            hdc = OpenHarmonyDeviceConnector.from_device(device)
            comm = OpenHarmonyCommLayer(hdc)
            platform = Platform(comm)
        case Target.ANDROID:
            from benchkit.devices.adb import AndroidCommLayer, AndroidDebugBridge
            
            bench_dir = "/data/local/tmp"
            device = list(AndroidDebugBridge.query_devices())[0]
            adb = AndroidDebugBridge.from_device(device) 
            comm = AndroidCommLayer(adb)
            platform = Platform(comm)
        case Target.CONTAINER:
            from rustcontainer import get_rust_docker_platform

            platform = get_rust_docker_platform(host_dir=this_dir)
            bench_dir = "/home/user/workspace/mnt/ipc_runner"

    benchmark = IPCBenchmark(
        bench_dir=bench_dir,
        platform=platform,
        target=target,
        skip_rebuild=skip_rebuild,
    )

    benchmark._base_data_dir = None

    campaign = CampaignIterateVariables(
        name="IPC Benching",
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        gdb=False,
        debug=False,
        constants=None,
        enable_data_dir=False,
    )

    campaigns: List[Campaign] = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_graph(
        plot_name="lineplot",
        x="m",
        y="time_seconds",
    )


if __name__ == "__main__":
    main()
