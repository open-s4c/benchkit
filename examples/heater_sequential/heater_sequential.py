# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import re
from typing import Any, Dict, Iterable, List

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType


class HeaterSeqBench(Benchmark):
    """Benchmark object for Heater Sequential benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform | None = None,
        build_dir: PathType | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform

        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path) and self.platform.comm.isfile(
            bench_src_path / "heater.c"
        ):
            raise ValueError(
                f"Invalid Heater source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path

        if build_dir is None:
            self._build_dir = self._bench_src_path / f"build-{self.platform.hostname}"
            self._tmpdb_dir = "/tmp/benchkit_heater_seq"
        else:
            self._build_dir = self._bench_src_path / build_dir
            self._tmpdb_dir = self._build_dir / "tmp" / "benchkit_heater_seq"

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "cpu",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    @staticmethod
    def _parse_results(
        output: str,
    ) -> Dict[str, str]:
        match = re.search(r"Operations performed:\s*(\d+)", output)
        if not match:
            raise ValueError(f"Could not find 'Operations performed' in output:\n{output}")

        result_dict = dict()
        result_dict["ops"] = int(match.group(1))

        return result_dict

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("gcc"),
        ]

    def build_tilt(self, **kwargs) -> None:
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs) -> None:
        build_dir = self._build_dir
        self.platform.comm.makedirs(path=build_dir, exist_ok=True)

        self.platform.comm.shell(
            command=f"gcc -O3 -o heater {self._bench_src_path / 'heater.c'}",
            current_dir=build_dir,
            output_is_log=True,
        )

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        cpu: int = 1,
        **kwargs,
    ) -> str:
        run_command = [
            "./heater",
            f"{benchmark_duration_seconds}",
            f"{cpu}",
        ]

        environment = self._preload_env(
            **kwargs,
        )

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._build_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = self._parse_results(output=command_output)
        return result_dict
