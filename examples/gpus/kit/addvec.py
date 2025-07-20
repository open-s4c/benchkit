# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict, List

from benchkit.benchmark import Benchmark, PostRunHook
from benchkit.commandwrappers import CommandWrapper
from benchkit.platforms import Platform
from benchkit.utils.types import PathType


class AddVecBench(Benchmark):
    def __init__(
        self,
        platform: Platform,
        src_dir: PathType,
        command_wrappers: List[CommandWrapper] = (),
        post_run_hooks: List[PostRunHook] = (),
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=post_run_hooks,
        )
        self.platform = platform
        self._bench_src_path = Path(src_dir)

    @property
    def bench_src_path(self) -> Path:
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
