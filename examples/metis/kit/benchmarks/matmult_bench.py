# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Benchkit support for the Metis benchmarks.
"""

import pathlib
import shutil
from typing import Any, Dict, List

from benchkit.benchmark import Benchmark
from benchkit.utils.dir import get_curdir, parentdir
from output_parser import parse_output

_COMMAND_LINE_ARGS = {
	"nb_procs": "-p",
	"nb_tasks_map": "-m",
	"matrix_length": "-l",
	"silent": "-q",
}

class MatrixMultBench(Benchmark):
	"""Benchmark object for Metis matrix_multiply benchmark."""

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
			"nb_procs",
			"nb_tasks_map",
			"matrix_length",
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
		nb_procs: int,
		nb_tasks_map: int,
		matrix_length: int,
		silent: bool,
		**kwargs,
	) -> str:
		run_command = [
			f"./{benchmark_name}",
			f"{_COMMAND_LINE_ARGS['nb_procs']} {nb_procs}",
			f"{_COMMAND_LINE_ARGS['nb_tasks_map']} {nb_tasks_map}",
			f"{_COMMAND_LINE_ARGS['matrix_length']} {matrix_length}",
		]

		if silent:
			run_command.append(_COMMAND_LINE_ARGS["silent"])

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
