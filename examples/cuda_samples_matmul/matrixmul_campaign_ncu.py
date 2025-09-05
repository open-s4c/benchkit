#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import numpy as np
import shutil
from typing import Any, Dict, List, Iterable

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.commandwrappers.ncu2 import NcuWrap, CommandWrapper
from benchkit.platforms import Platform
from benchkit.utils.types import PathType
from benchkit.sharedlibs import SharedLib
from benchkit.utils.dir import get_curdir, parentdir
from benchkit.platforms import get_current_platform

ncu_wrapper = NcuWrap(metrics=["smsp__sass_l1tex_tags_mem_global"], csv=True, report_or_log=True)

# MA_WIDTHS = [32,64,128,256,512]
# MA_HEIGHTS = [32,64,128,256,512]
# MB_HEIGHTS = [32,64,128,256,512]

MA_WIDTHS = [32,64]
MA_HEIGHTS = [32,64]
MB_WIDTHS = [32,64]

class MatrixMulBench(Benchmark):
    def __init__(
        self,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform | None = None,
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

        if platform is not None:
            self.platform = platform

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    '''
    Because this is matrix multiplication the outer dims of the 2 matrices have to match
    As a result mb_width = ma_height
    '''
    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "ma_width",
            "ma_height",
            "mb_width"
        ]

    @staticmethod
    def get_tilt_var_names():
        return []

    def build_bench(
        self,
        **kwargs,
    ) -> None:

        if self._build_dir.is_dir() and len(str(self._build_dir)) > 4:
            shutil.rmtree(str(self._build_dir))

        self.platform.comm.makedirs(path=self._build_dir, exist_ok=True)

        self.platform.comm.shell(
            command="make",
            current_dir=self._bench_src_path,
            output_is_log=True,
        )

    def single_run(
        self,
        ma_width: int,
        ma_height: int,
        mb_width: int,
        **kwargs,
    ) -> str:
        current_dir = self._build_dir
        environment = self._preload_env(**kwargs)

        run_command = [
            "./matrixMul",
            f"-wA={ma_width}",
            f"-hA={ma_height}",
            f"-wB={mb_width}",
            f"-hB={ma_width}"
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
        output: str
    ) -> Dict[str, Any]:
        output_lines = output.splitlines()
        result_line = next(line for line in output_lines if line.startswith("Performance="))
        sections = result_line.split(',')
        names=[
            "ma_width",
            "ma_height",
            "mb_width",
            "ma_width",
            "GFlops/s",
            "Time ms",
            "Ops",
            "Workgroup Size"
        ]
        values = [ma_width,ma_height,ma_height,mb_width]

        gflops = " "
        ops = " "
        time = " "
        wgsize = " "

        for section in sections:
            if "GFlop/s" in section:
                words = section.split()
                gflops = words[1]
            if "Ops" in section:
                words = section.split()
                ops = words[1] 
            if "Time" in section:
                words = section.split()
                time = words[1]
            if "WorkgroupSize" in section:
                words = section.split()
                wgsize = words[1]

        values.append(gflops)
        values.append(ops)
        values.append(time)
        values.append(wgsize)

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

        result_dict = self._parse_results(
            ma_width,
            ma_height,
            mb_width,
            command_output)

        return result_dict


def main():
    nb_runs = 3
    platform = get_current_platform()

    bench = MatrixMulBench(
        platform=platform,
        command_wrappers=[ncu_wrapper],
        post_run_hooks=[ncu_wrapper.post_run_hook_update_results]
    )

    campaign = CampaignCartesianProduct(
        name="gpumatmul_ncu",
        benchmark=bench,
        nb_runs=nb_runs,
        variables={
            "ma_width": MA_WIDTHS,
            "ma_height": MA_HEIGHTS,
            "mb_width": MB_WIDTHS
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

    # campaign_suite.generate_graph(
    #     plot_name="barplot",
    #     title=f"Add vector on GPU ({nb_runs} runs)",
    #     y="kernel_compute_seconds",
    #     x="block_size",
    # )


if __name__ == "__main__":
    main()
