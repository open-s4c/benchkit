# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Benchkit support for the Metis benchmarks.
"""

import pathlib
from typing import Any, Dict, List

from output_parser import parse_output

from benchkit.benchmark import Benchmark
from benchkit.utils.dir import get_curdir, parentdir

_COMMAND_LINE_ARGS = {
    "nb_procs": "-p",
    "nb_tasks_map": "-m",
    "nb_tasks_reduce": "-r",
    "nb_top_values": "-l",
    "silent": "-q",
}


class KMeansBench(Benchmark):
    """Benchmark object for Metis kmeans benchmark."""

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
        bench_path = parentdir(path=script_path, levels=2) / "deps/Metis"

        self._bench_src_path = bench_path
        self._build_dir = bench_path / "obj"

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "benchmark_name",
            "vector_dim",
            "nb_clusters",
            "nb_points",
            "max_value",
            "nb_procs",
            "nb_tasks_map",
            "nb_tasks_reduce",
            "nb_top_values",
            "silent",
        ]

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
        **_kwargs,
    ) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    def single_run(
        self,
        benchmark_name: str,
        vector_dim: int,
        nb_clusters: int,
        nb_points: int,
        max_value: int,
        nb_procs: int,
        nb_tasks_map: int,
        nb_tasks_reduce: int,
        nb_top_values: int,
        silent: bool,
        **kwargs,
    ) -> str:
        run_command = [
            f"./{benchmark_name}",
            f"{vector_dim}",
            f"{nb_clusters}",
            f"{nb_points}",
            f"{max_value}",
            f"{_COMMAND_LINE_ARGS['nb_procs']} {nb_procs}",
            f"{_COMMAND_LINE_ARGS['nb_tasks_map']} {nb_tasks_map}",
            f"{_COMMAND_LINE_ARGS['nb_tasks_reduce']} {nb_tasks_reduce}",
            f"{_COMMAND_LINE_ARGS['nb_top_values']} {nb_top_values}",
        ]

        if silent:
            run_command.append(f"{_COMMAND_LINE_ARGS['silent']}")

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
        result_dict = parse_output(command_output)
        return result_dict
