# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Benchkit support for the Metis benchmarks.
"""

import pathlib
import os
import shutil
from typing import Any, Dict, List

from benchkit.benchmark import Benchmark
from benchkit.platforms import Platform
from benchkit.utils.dir import get_curdir, parentdir
from output_parser import parse_output

_COMMAND_LINE_ARGS = {
	"nb_procs": "-p",
	"nb_tasks_map": "-m",
	"nb_tasks_reduce": "-r",
	"nb_top_values": "-l",
	"silent": "-q",
}

_DATA_FILE_NAMES = {
	"wr_1": "wr/100MB_1M_Keys.txt",
	"wr_2": "wr/100MB_100K_Keys.txt",
	"wr_3": "wr/800MB.txt",
	"wr_4": "wr/500MB.txt",
	"test": "wc/10MB.txt",
}

class WRBench(Benchmark):
	"""Benchmark object for Metis hist benchmark."""

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
		
		# self._data_filenames = {
		# 	"test": "wc/10MB.txt",
		# 	"bench": "wc/300MB_1M_Keys.txt"
		# }

	@property
	def bench_src_path(self) -> pathlib.Path:
		return self._bench_src_path

	@staticmethod
	def get_build_var_names() -> List[str]:
		return []

	@staticmethod
	def get_run_var_names() -> List[str]:
		return [
			"data_path",
		]

	@staticmethod
	def get_tilt_var_names() -> List[str]:
		return []

	def prebuild_bench(  # pylint: disable=arguments-differ
		self,
		benchmark_duration_seconds: int,
	) -> None:
		data_dir = os.path.join(self._bench_src_path, "data")
		wr_1_file_path = os.path.join(data_dir, _DATA_FILE_NAMES["wr_1"])
		wr_2_file_path = os.path.join(data_dir, _DATA_FILE_NAMES["wr_2"])
		wr_3_file_path = os.path.join(data_dir, _DATA_FILE_NAMES["wr_3"])
		wr_4_file_path = os.path.join(data_dir, _DATA_FILE_NAMES["wr_4"])

		temp_file_path = os.path.join(data_dir, "wr/temp_5MB.txt~")
		data_tool_path = os.path.join(self._bench_src_path, "data_tool")

		# Ensure that data file exists
		if not os.path.isfile(wr_1_file_path):
			raise FileNotFoundError(f"Data file not found: {wr_1_file_path}")

		if not os.path.isfile(wr_2_file_path):
			raise FileNotFoundError(f"Data file not found: {wr_2_file_path}")

		# Generate wr input with many keys and many duplicates
		if not os.path.isfile(wr_3_file_path):
			print("[INFO] Creating benchmark data file...")

			# Read 5MB from source and write to temp
			with open(wr_1_file_path, "rb") as f_in, open(temp_file_path, "wb") as f_out:
				f_out.write(f_in.read(5_000_000))

			# Start with one copy, then append 160 more
			shutil.copy(temp_file_path, wr_3_file_path)			
			with open(temp_file_path, "rb") as chunk, open(wr_3_file_path, "ab") as out_file:
				content = chunk.read()
				for _ in range(160):
					out_file.write(content)

			self.platform.comm.remove(temp_file_path, recursive=False)

		# Generate wr input with many keys and many duplicates, but unpredicatable
		if not os.path.isfile(wr_4_file_path):
			if not os.path.isfile(os.path.join(data_tool_path, "gen")):
				print("[INFO] Compiling data generation tool...")
				self.platform.comm.shell(
					command="g++ gen.cc -o gen",
					current_dir=data_tool_path,
				)

			print("[INFO] Creating benchmark data file...")			
			self.platform.comm.pipe_shell(
				f"./gen 500000 4 > {wr_4_file_path}",
				current_dir=data_tool_path,
			)
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
		data_path: str,
		**kwargs,
	) -> str:
		# data_file = self._data_filenames["test"] if test_run else self._data_filenames["bench"]

		benchmark_name = self._constants.get("benchmark_name")
		nb_procs = self._constants.get("nb_procs")
		nb_tasks_map = self._constants.get("nb_tasks_map")
		nb_tasks_reduce = self._constants.get("nb_tasks_reduce")
		nb_top_values = self._constants.get("nb_top_values")
		silent = self._constants.get("silent")

		run_command = [
			f"./{benchmark_name}",
			f"../data/{data_path}",
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
