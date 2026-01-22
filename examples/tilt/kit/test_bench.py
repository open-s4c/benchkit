# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
from typing import Any, Dict, Iterable, List

from benchkit.benchmark import (
	Benchmark,
	CommandAttachment,
	CommandWrapper,
	PostRunHook,
	PreRunHook,
	SharedLib,
)
from benchkit.platforms import Platform
from benchkit.utils.dir import caller_dir
from benchkit.utils.types import PathType

from tiltlib import cmake_configure_build

class SimpleMutexTestBench(Benchmark):
	"""Benchmark object for testing if our lock implementations for simple mutex operations work."""
	def __init__(
		self,
		src_dir: PathType = "",
		command_wrappers: Iterable[CommandWrapper] = (),
		command_attachments: Iterable[CommandAttachment] = (),
		shared_libs: Iterable[SharedLib] = (),
		pre_run_hooks: Iterable[PreRunHook] = (),
		post_run_hooks: Iterable[PostRunHook] = (),
		platform: Platform = None,
	) -> None:
		super().__init__(
			command_wrappers=command_wrappers,
			command_attachments=command_attachments,
			shared_libs=shared_libs,
			pre_run_hooks=pre_run_hooks,
			post_run_hooks=post_run_hooks,
		)
		if platform is not None:
			self.platform = platform
		if src_dir:
			self._src_dir = pathlib.Path(src_dir).resolve()
		else:
			self._src_dir = (caller_dir() / "../bench").resolve()
		self._build_dir = self._src_dir / f"build-{self.platform.hostname}"

	@property
	def bench_src_path(self) -> pathlib.Path:
		return self._src_dir

	@staticmethod
	def get_build_var_names() -> List[str]:
		return [
			# "benchmark_duration_seconds",
			# "lock",
		]

	@staticmethod
	def get_run_var_names() -> List[str]:
		return [
			# "benchmark_name",
			# "lock",
		]

	def clean_bench(self) -> None:
		pass

	# def prebuild_bench(
	#     self,
	#     **kwargs,
	# ) -> int:
		
	#     print("[INFO] Building bench...")
	#     cmake_configure_build(
	#         platform=self.platform,
	#         src_dir=self.bench_src_path,
	#         build_dir=self._build_dir,
	#         debug=self.must_debug(),
	#         make_suffix=self._parallel_make_str(),
	#     )
	#     return 0

	def prebuild_bench(
		self,
		**kwargs,
	) -> None:
		pass

	def build_bench(
		self,
		**kwargs,
	) -> int:
		cmake_configure_build(
			platform=self.platform,
			src_dir=self.bench_src_path,
			build_dir=self._build_dir,
			debug=self.must_debug(),
			make_suffix=self._parallel_make_str(),
		)
		return 0

	def single_run(
		self,
		**kwargs,
	) -> str:
		current_dir = self._build_dir
		environment = self._preload_env(
			**kwargs,
		)
		benchmark_name = self._constants.get("benchmark_name")
		run_command = [f"./{benchmark_name}"]

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
			print_output=False,
			ignore_ret_codes=(1,),
		)
		print(output)
		return output

	def parse_output_to_results(  # pylint: disable=arguments-differ
		self,
		command_output: str,
		**_kwargs,
	) -> Dict[str, Any]:
		result_dict = {}
		return result_dict
