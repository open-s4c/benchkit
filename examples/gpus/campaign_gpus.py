#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
from typing import Any, Dict, List

from gpus import get_gpu_docker_platform

from benchkit.benchmark import Benchmark
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.platforms import Platform
from benchkit.utils.dir import caller_dir
from benchkit.utils.types import PathType

GUEST_SRC_DIR = "/home/user/src"


class AddVecBench(Benchmark):
    def __init__(
        self,
        platform: Platform,
        src_dir: PathType,
    ) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=(),
        )
        self.platform = platform
        self._bench_src_path = pathlib.Path(src_dir)

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return ["block_size"]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return []

    def build_bench(
        self,
        block_size: int,
        **kwargs,
    ) -> None:
        self.platform.comm.shell(
            command=f"nvcc add.cu -DBLOCK_SIZE={block_size} -o add_cuda",
            current_dir=f"{self._bench_src_path}",
            output_is_log=True,
        )

    def single_run(
        self,
        **kwargs,
    ) -> str:
        current_dir = self.bench_src_path
        environment = self._preload_env(**kwargs)

        run_command = ["./add_cuda"]
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

    def parse_output_to_results(
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}

        i = command_output.index("Outputs:")
        lines = command_output[i:].splitlines()
        for line in lines[1:]:
            if ":" in line:
                print(line)
                left, right = line.rsplit(":")
                result_dict[left.strip()] = right.strip()

        return result_dict


def get_docker_platform() -> Platform:
    host_src_dir = (caller_dir() / "src").resolve()

    platform = get_gpu_docker_platform(
        host_src_dir=host_src_dir,
        guest_src_dir=GUEST_SRC_DIR,
    )

    return platform


def main():
    nb_runs = 3
    platform = get_docker_platform()

    bench = AddVecBench(
        platform=platform,
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
