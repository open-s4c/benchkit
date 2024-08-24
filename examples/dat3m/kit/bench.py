# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import re
from typing import Any, Dict, Iterable, List

from benchkit.benchmark import (
    Benchmark,
    CommandAttachment,
    CommandWrapper,
    PostRunHook,
    PreRunHook,
    SharedLib,
)
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.utils.misc import TimeMeasure
from benchkit.utils.types import PathType


class Dat3mBench(Benchmark):
    """Benchmark object for Dat3m benchmark."""

    def __init__(
        self,
        src_dir: PathType,
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
        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform

        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path):
            raise ValueError(
                f"Invalid source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path
        self._build_dir = bench_src_path

        self.dat3m_memorymodels = [
            mm[:-4]
            for elem in self.platform.comm.shell(command="ls -1 cat").splitlines()
            if (mm := elem.strip()).endswith(".cat")
        ]
        self.dat3m_locks = [
            lock[:-2]
            for elem in self.platform.comm.shell(command="ls -1 benchmarks/locks").splitlines()
            if (lock := elem.strip()).endswith(".c")
        ]
        self.dat3m_targets = [
            "c11",
            "arm8",
            "power",
            "ptx",
            "tso",
            "imm",
            "lkmm",
            "riscv",
            "vulkan",
        ]
        self._tmp_results = {}

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "memory_model",
            "target_arch",
            "lock_name",
            "bound",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + []

    def build_tilt(self, **kwargs) -> None:
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(
        self,
        **_kwargs,
    ) -> None:
        pass

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
        memory_model: str = "aarch64",
        target_arch: str = "arm8",
        lock_name: str = "ttas",
        bound: int | None = None,
        **kwargs,
    ) -> str:
        # Sanitize input variables
        if memory_model not in self.dat3m_memorymodels:
            raise ValueError(
                (
                    f"Unknown memory model: "
                    f"{memory_model}\n"
                    f"Supported memory models: {self.dat3m_memorymodels}"
                )
            )
        if target_arch not in self.dat3m_targets:
            raise ValueError(
                (
                    f"Unknown target architecture: "
                    f"{target_arch}\nSupported targets: {self.dat3m_targets}"
                )
            )
        if lock_name not in self.dat3m_locks:
            raise ValueError(
                (f"Unknown lock name: " f"{lock_name}\nSupported locks: {self.dat3m_locks}")
            )

        # Generate environment
        environment = self._preload_env(
            benchmark_duration_seconds=benchmark_duration_seconds,
            memory_model=memory_model,
            target_arch=target_arch,
            lock_name=lock_name,
            bound=bound,
            **kwargs,
        )

        dat3m_home_env = self.platform.comm.shell(
            command="printenv DAT3M_HOME",
            print_output=False,
            print_curdir=False,
        ).strip()
        dat3m_home = pathlib.Path(dat3m_home_env) if dat3m_home_env else ""
        dat3m_jar = dat3m_home / "dartagnan/target/dartagnan.jar"
        dat3m_lock = dat3m_home / f"benchmarks/locks/{lock_name}.c"

        # Generate dat3m command line using variables
        command_head = [
            "java",
            "-jar",
            f"{dat3m_jar}",
        ]
        command_opts = [
            f"cat/{memory_model}.cat",
            f"--target={target_arch}",
        ]
        if bound is not None:
            command_opts.append(f"--bound={bound}")
        command_tail = [f"{dat3m_lock}"]
        run_command = command_head + command_opts + command_tail

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        # Run the actual command
        with TimeMeasure() as time_measure:
            output = self.run_bench_command(
                run_command=run_command,
                wrapped_run_command=wrapped_run_command,
                current_dir=self._build_dir,
                environment=environment,
                wrapped_environment=wrapped_environment,
                print_output=True,
            )
        self._tmp_results["benchkit/runtime_s"] = time_measure.duration_seconds

        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}

        # Parsing summary
        lines = [line.strip() for line in command_output.splitlines()]
        summary_lines = lines[lines.index("======== Summary ========") :]
        secs_pattern = re.compile(r"(.*?):\s*([\d.]+)\s*secs")  # to match lines with 'secs'
        other_pattern = re.compile(r"(.*?):\s*(\d+)")  # to match other lines
        for line in summary_lines:
            if "Verification finished" in line:
                break
            if secs_match := secs_pattern.match(line):
                key, value = secs_match.groups()
                key = key.lstrip("-- ")
                key = key.replace("#", "Nb ")
                result_dict[f"dat3m/summary/{key.strip()} (seconds)"] = float(value)
            elif other_match := other_pattern.match(line):
                key, value = other_match.groups()
                key = key.lstrip("-- ")
                key = key.replace("#", "Nb ")
                result_dict[f"dat3m/summary/{key.strip()}"] = int(value)

        # Parsing status
        start = -1
        for i, line in enumerate(lines, start=0):
            if "Verification finished with result" in line:
                start = i
                break
        if -1 != start:
            result_lines = lines[start:]
            match = re.match(
                pattern=r".*Verification finished with result (\w+)$",
                string=result_lines[0],
            )
            if match is not None:
                result_dict["dat3m/status_log"] = match.group(1)
        result_dict["dat3m/status"] = lines[-2]
        if (m := secs_pattern.match(lines[-1])) is not None:
            key, value = m.groups()
            key = key.lstrip("-- ")
            result_dict[f"dat3m/{key.strip()} (seconds)"] = float(value)

        result_dict |= self._tmp_results
        return result_dict
