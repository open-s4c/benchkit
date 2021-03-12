# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for the custom VSync lock microbenchmarks.
"""

import pathlib
import shutil
from typing import Any, Dict, List

from benchkit.benchmark import Benchmark
from benchkit.utils.dir import get_curdir, parentdir


class LockMicroBench(Benchmark):
    """Benchmark object for VSync lock micro benchmark."""

    def __init__(
        self,
    ) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=(),
        )

        script_path = get_curdir(__file__)
        bench_path = parentdir(path=script_path, levels=1) / "microbench"

        self._bench_src_path = bench_path
        self._build_dir = bench_path / "build"

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            "lock",
            "nb_threads",
            "benchmark_duration_seconds",
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return []

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def prebuild_bench(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
    ) -> None:
        pass

    def build_bench(  # pylint: disable=arguments-differ
        self,
        lock: str,
        nb_threads: int,
        benchmark_duration_seconds: int,
    ) -> None:
        duration = benchmark_duration_seconds
        build_dir = self._build_dir

        if self._build_dir.is_dir() and len(str(build_dir)) > 4:
            shutil.rmtree(str(self._build_dir))

        # Create build directory
        self.platform.comm.makedirs(path=build_dir, exist_ok=True)

        # Configure with cmake
        debug_flag = "Debug" if self.must_debug() else "Release"
        cmake_command = [
            "cmake",
            f"-DLOCK={lock}",
            f"-DNB_THREADS={nb_threads}",
            f"-DRUN_DURATION_SECONDS={duration}",
            f"-DCMAKE_BUILD_TYPE={debug_flag}",
            f"{self._bench_src_path}",
        ]
        self.platform.comm.shell(
            command=cmake_command,
            current_dir=build_dir,
            output_is_log=True,
        )

        # Compile with make
        self.platform.comm.shell(
            command="make",
            current_dir=build_dir,
            output_is_log=True,
        )

    def clean_bench(self) -> None:
        pass

    def single_run(
        self,
        **kwargs,
    ) -> str:
        run_command = ["./libvsync-locks"]

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=run_command,
            current_dir=self._build_dir,
            environment=None,
            wrapped_environment=None,
            print_output=True,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        key_seq_values = command_output.strip().split(";")
        result_dict = dict(map(lambda s: s.split("="), key_seq_values))
        return result_dict
