#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import numpy as np
from typing import Any, Dict, List, Iterable

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.commandwrappers.ncu import NcuWrap, CommandWrapper
from benchkit.platforms import Platform
from benchkit.utils.types import PathType
from benchkit.sharedlibs import SharedLib
from benchkit.utils.dir import get_curdir, parentdir

ncu_wrapper = NcuWrap("./",enable_nvtx=True,set="full")

MA_WIDTHS = [32,64,128,256,512]
MA_HEIGHTS = [32,64,128,256,512]
MB_WIDTHS = [32,64,128,256,512]
MB_HEIGHTS = [32,64,128,256,512]

class MatrixMulBench(Benchmark):
    def __init__(
        self,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        platform: Platform,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )

        script_path = get_curdir(__file__)
        bench_path = script_path / "src"
        build_path = script_path / "build"

        self._bench_src_path = bench_path
        self._build_dir = build_path

        self.platform = platform

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "ma_width",
            "ma_height",
            "mb_width",
            "mb_height"
        ]

    @staticmethod
    def get_tilt_var_names():
        return []

    def build_bench(
        self,
        **kwargs,
    ) -> None:

        cmake_command = [
            "cmake",
            f"{self._bench_src_path}"
        ]

        self.platform.comm.shell(
            command=cmake_command,
            current_dir=self._build_dir,
            output_is_log=True,
        )

        self.platform.comm.shell(
            command="make",
            current_dir=self._build_dir,
            output_is_log=True,
        )

    def single_run(
        self,
        ma_width: int,
        ma_height: int,
        mb_width: int,
        mb_height: int,
        **kwargs,
    ) -> str:
        current_dir = self._build_dir
        environment = self._preload_env(**kwargs)

        run_command = [
            "./matrixMul",
            f"-wA={ma_width}",
            f"-hA={ma_height}",
            f"-wB={mb_width}",
            f"-hB={mb_height}"
        ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=current_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=True,
        )

        return output

    @staticmethod
    def _parse_results(
        ma_width: int,
        ma_height: int,
        mb_width: int,
        mb_height: int,
        output: str
    ) -> Dict[str, Any]:
        output_lines = output.splitlines()
        result_line = next(line for line in output_lines if line.startswith("Performance="))
        words = result_line.split()[1:-1]
        names=[
            "ma_width",
            "ma_height",
            "mb_width",
            "mb_height",
            "GFlops/s",
            "Time ms",
            "Ops",
            "Workgroup Size"
        ]
        values = [ma_width,ma_height,mb_width,mb_height]

        try:
            gflops_idx = words.index('GFlop/s,') - 1
            values.append(words[gflops_idx])
        except ValueError:
            values.append(0)
            print("GFlops/s could not be recorded...")

        try:
            time_idx = words.index('Time=') + 1
            values.append(words[time_idx])
        except ValueError:
            values.append(0)
            print("Time could not be recorded...")

        try:
            ops_idx = words.index('Ops,') - 1
            values.append(words[ops_idx])
        except ValueError:
            values.append(0)
            print("Ops could not be recorded...")
        
        try:
            workgroup_idx = words.index('WorkgroupSize=') + 1
            values.append(words[workgroup_idx])
        except ValueError:
            values.append(0)
            print("Workgroup size could not be recorded...")

        result_dict = dict(zip(names,values))

        return result_dict


    def parse_output_to_results(
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}

        ma_width = int(run_variables["ma_width"])
        ma_height = int(run_variables["ma_height"])
        mb_width = int(run_variables["mb_width"])
        mb_height = int(run_variables["mb_height"])

        result_dict = self._parse_results(
            ma_width,
            ma_height,
            mb_width,
            mb_height,
            command_output)

        return result_dict


def main():
    nb_runs = 3
    # platform = get_docker_platform()

    bench = MatrixMulBench(
        src_dir=GUEST_SRC_DIR,
    )

    campaign = CampaignCartesianProduct(
        name="gpuaddvec",
        benchmark=bench,
        nb_runs=nb_runs,
        variables={
            "block_size": [1, 2, 16, 256, 2048, 4096, 8192, 16384, 32768],
        },
        constants={},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    campaign_suite = CampaignSuite(campaigns=[campaign])
    campaign_suite.run_suite()

    campaign_suite.generate_graph(
        plot_name="barplot",
        title=f"Add vector on GPU ({nb_runs} runs)",
        y="kernel_compute_seconds",
        x="block_size",
    )


if __name__ == "__main__":
    main()
