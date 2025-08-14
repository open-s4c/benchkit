# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Benchkit support for the Metis benchmarks.
"""

import pathlib
import shutil
import os
from typing import Any, Dict, List

from benchkit.benchmark import Benchmark
from benchkit.utils.dir import get_curdir, parentdir
from output_parser import parse_output

_COMMAND_LINE_ARGS = {
	"nb_procs": "-p",
	"nb_tasks_map": "-m",
	"silent": "-q",
}

_DATA_FILE_NAMES = {
	"test": "lr_10MB.txt",
	"bench": "lr_4GB.txt"
}

class LinRegBench(Benchmark):
	"""Benchmark object for Metis linear_regression benchmark."""

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
			"test_run",
			"silent",
		]

	@staticmethod
	def get_tilt_var_names() -> List[str]:
		return []

	def prebuild_bench(  # pylint: disable=arguments-differ
		self,
		benchmark_duration_seconds: int,
	) -> None:
		data_dir = os.path.join(self._bench_src_path, "data")
		data_bench_file_path = os.path.join(data_dir, _DATA_FILE_NAMES["bench"])
		data_test_file_path = os.path.join(data_dir, _DATA_FILE_NAMES["test"])

		if not os.path.isfile(data_test_file_path):
			os.makedirs(data_dir, exist_ok=True)
			print("[INFO] Creating test data file...")
			with open(data_test_file_path, "wb") as f_test:
				f_test.write(os.urandom(10 * 1024 * 1024))
			
		if not os.path.isfile(data_bench_file_path):
			print("[INFO] Creating benchmark data file...")
			with open(data_test_file_path, "rb") as f_test, open(data_bench_file_path, "wb") as f_bench:
				chunk = f_test.read()
				for _ in range(400):
					f_bench.write(chunk)
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
		test_run: bool,
		silent: bool,
		**kwargs,
	) -> str:
		data_file = _DATA_FILE_NAMES["test"] if test_run else _DATA_FILE_NAMES["bench"]
		run_command = [
			f"./{benchmark_name}",
			f"../data/{data_file}",
			f"{_COMMAND_LINE_ARGS['nb_procs']} {nb_procs}",
			f"{_COMMAND_LINE_ARGS['nb_tasks_map']} {nb_tasks_map}",
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
