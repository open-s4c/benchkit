# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for Kyoto Cabinet benchmark.
See: https://dbmx.net/kyotocabinet/
"""

import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import (
    Benchmark,
    CommandAttachment,
    PostRunHook,
    PreRunHook,
    RecordParameters,
    RecordResult,
)
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.dir import get_curdir
from benchkit.utils.types import CpuOrder, PathType


def _kccachetest_parse_output(output_lines) -> Dict[str, Any]:
    result_dict = {}
    thread_dict = {}

    for line in output_lines:
        if line.startswith("buckets:"):
            gd = re.match(
                pattern=r"buckets: (?P<buckets>\d+) \(used=(?P<used>\d+)\) \(load=(?P<load>.+)\)",
                string=line,
            ).groupdict()
            result_dict["buckets"] = int(gd["buckets"])
            result_dict["buckets_used"] = int(gd["used"])
            result_dict["load"] = str(gd["load"])
        elif line.startswith("count:"):
            gd = re.match(
                pattern=r"count: (?P<count>\d+) (.+) \(capcnt=(?P<capcnt>\d+)\)",
                string=line,
            ).groupdict()
            result_dict["kccount"] = int(gd["count"])
            result_dict["capcnt"] = int(gd["capcnt"])
        elif line.startswith("size:"):
            gd = re.match(
                pattern=r"size: (?P<size_bytes>\d+) \(.+\) \(capsiz=(?P<capsiz>.+)\)",
                string=line,
            ).groupdict()
            result_dict["size_bytes"] = int(gd["size_bytes"])
            result_dict["capsiz"] = int(gd["capsiz"])
        elif line.startswith("memory:"):
            gd = re.match(
                pattern=r"memory: (?P<memory>\d+)",
                string=line,
            ).groupdict()
            result_dict["memory"] = int(gd["memory"])
        elif line.startswith("time:"):
            gd = re.match(
                pattern=r"time: (?P<time>\d+)",
                string=line,
            ).groupdict()
            result_dict["duration"] = int(gd["time"])
        elif line.startswith("iterations thread"):
            gd = re.match(
                pattern=r"iterations thread (?P<tid>\d+): (?P<thread_count>\d+)",
                string=line,
            )
            thread_dict[f'thread_{gd["tid"]}'] = gd["thread_count"]
        elif line.startswith("total iterations"):
            gd = re.match(
                pattern=r"total iterations: (?P<thread_count>\d+)",
                string=line,
            )
            result_dict["global_count"] = gd["thread_count"]

    result_dict.update(thread_dict)
    return result_dict


class KyotoCabinetBench(Benchmark):
    """Benchmark object for Kyoto Cabinet benchmark."""

    def __init__(
        self,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        platform: Platform | None = None,
        src_dir: PathType | None = None,
    ):
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform

        if src_dir is None:
            if not platform.comm.is_local:
                raise ValueError("Remote benchmark must define src_dir")  # TODO recurrent pattern
            script_path = get_curdir(__file__)
            bench_src_path = script_path.parent.resolve()
        else:
            bench_src_path = pathlib.Path(src_dir)
        self._bench_src_path = bench_src_path

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "test_name",
            "cpu_order",
            "master_thread_core",
            "nb_threads",
            "lock",
            "atomics",
            "use_lse",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return [
            "lock",
            "atomics",
            "use_lse",
        ]

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
        ]

    def build_tilt(self, **kwargs) -> None:
        # TODO compile tilt with the thread shift, otherwise everything is shifted
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(  # pylint: disable=arguments-differ
        self,
        **_kwargs,
    ) -> None:
        bench_dir = self._bench_src_path
        makefile = bench_dir / "Makefile"

        if not makefile.is_file():
            debug_flag = ["--enable-debug"] if self.must_debug() else []
            self.platform.comm.shell(
                command=["./configure"] + debug_flag,
                current_dir=bench_dir,
                output_is_log=True,
            )
        self.platform.comm.shell(
            command=f"make{self._parallel_make_str()}",
            current_dir=bench_dir,
            output_is_log=True,
        )
        self.platform.comm.shell(
            command=f"make{self._parallel_make_str()} benchmark",
            current_dir=bench_dir,
            output_is_log=True,
        )

    def build_bench(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
    ) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        lock: str = "",
        nb_threads: int = 2,
        cpu_order: CpuOrder = None,
        use_lse: bool = False,
        atomics: str = None,
        test_name: str = "",
        master_thread_core: int | None = None,
        **kwargs,
    ) -> str:
        environment = self._preload_env(
            lock=lock,
            use_lse=use_lse,
            atomics=atomics,
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            **kwargs,
        )
        if environment is None:
            environment = {"LD_LIBRARY_PATH": self._bench_src_path}
        else:
            environment["LD_LIBRARY_PATH"] = self._bench_src_path
        if "LD_PRELOAD" in environment and "libassign" in environment["LD_PRELOAD"]:
            if "ASSIGN_FIRST_THREAD" not in environment:
                # the first worker thread in kyoto is the third one
                # (TIDs 0 & 1 are background threads)
                environment["ASSIGN_FIRST_THREAD"] = "2"

        if "kccachetest" == test_name:
            run_command = [
                "./kccachetest",
                "wicked",
                "-th",
                str(nb_threads),
                "-d",
                str(benchmark_duration_seconds),
                "-capcnt",
                "10000",
                "1000000",
            ]
        else:
            run_command = [
                "./benchmark",
                "-t",
                str(nb_threads),
                "-d",
                str(benchmark_duration_seconds),
            ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self.bench_src_path,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        benchmark_duration_seconds: int,
        run_variables: RecordParameters,
        **_kwargs,
    ) -> RecordResult:
        test_name = self._get_run_variable_value(name="test_name", run_variables=run_variables)

        if "kccachetest" == test_name:
            output_lines = [line.strip() for line in command_output.splitlines()]
            result_dict = _kccachetest_parse_output(output_lines)
        else:
            output_lines = [line for line in command_output.splitlines() if "total_ops" in line]
            if len(output_lines) != 1:
                raise ValueError('Kyotocabinet: incoherent output, regarding "total_ops"')
            output_line = output_lines[0]

            total_ops = int(output_line.split("=")[1])

            result_dict = {
                "duration": benchmark_duration_seconds,
                "global_count": total_ops,
            }

        return result_dict


def kyotocabinet_campaign(
    name: str = "kyotocabinet_campaign",
    benchmark: Optional[KyotoCabinetBench] = None,
    src_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    test_name: Iterable[str] = ("",),
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    locks: Iterable[str] = (),
    cpu_order: Iterable[CpuOrder] = (),
    master_thread_core: Iterable[int | None] = (),
    use_lse: Iterable[bool] = (),
    atomics: Iterable[str] = (),
    nb_threads: Iterable[int] = (1,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the Kyoto Cabinet benchmark."""
    variables = {
        "test_name": test_name,
        "lock": locks,
        "cpu_order": cpu_order,
        "master_thread_core": master_thread_core,
        "use_lse": use_lse,
        "atomics": atomics,
        "nb_threads": nb_threads,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if benchmark is None:
        benchmark = KyotoCabinetBench(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
            src_dir=src_dir,
        )

    return CampaignCartesianProduct(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        constants=constants,
        debug=debug,
        gdb=gdb,
        enable_data_dir=enable_data_dir,
        continuing=continuing,
        benchmark_duration_seconds=benchmark_duration_seconds,
        pretty=pretty,
    )
