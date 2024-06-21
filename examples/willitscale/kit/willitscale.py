# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for the Will-it-Scale benchmark.
See: https://github.com/antonblanchard/will-it-scale
"""

import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType


class WillItScaleBench(Benchmark):
    """
    Benchmark object for Will-it-Scale benchmark.
    """

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
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

        # TODO duplication with LevelDB & perhaps many more in the future.
        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path) and self.platform.comm.isfile(
            bench_src_path / "main.c"
        ):
            raise ValueError(
                f"Invalid Will-it-Scale source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path

    @property
    def bench_src_path(self) -> str:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            "test_name",
            "warmup_iterations",
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "cpu_order",
            "master_thread_core",
            "use_custom_cpu_pinning",
            "nb_threads",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("libhwloc-dev"),
        ]

    def build_tilt(self, **kwargs) -> None:
        raise NotImplementedError("Tilt is not necessary for this benchmark.")

    def prebuild_bench(
        self,
        **_kwargs,
    ) -> None:
        self.platform.comm.shell(command="make clean", current_dir=self.bench_src_path)

    def build_bench(  # pylint: disable=arguments-differ
        self,
        test_name: str,
        warmup_iterations: int,
        **_kwargs,
    ) -> None:
        self.platform.comm.shell(
            command="make clean",
            current_dir=self.bench_src_path,
            print_input=True,
            print_output=True,
        )

        warmup_str = str(warmup_iterations)
        self.platform.comm.shell(
            command=f"make {test_name} WARMUP_ITERATIONS={warmup_str}",
            current_dir=self.bench_src_path,
            print_input=True,
            print_output=True,
        )

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        build_variables: Dict[str, Any],
        cpu_order: CpuOrder = None,
        use_custom_cpu_pinning: bool = False,
        nb_threads: int = 2,
        master_thread_core: Optional[int] = None,
        **kwargs,
    ) -> str:
        if cpu_order is not None and use_custom_cpu_pinning:
            raise ValueError(
                "Cannot define benchkit cpu_order and custom cpu pinning "
                "from will-it-scale at the same time."
            )

        test_name: str = build_variables["test_name"]

        environment = self._preload_env(
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            **kwargs,
        )
        run_command = [
            f"./{test_name}",
            "-t",
            f"{nb_threads}",
            "-s",
            f"{benchmark_duration_seconds}",
        ] + ([] if use_custom_cpu_pinning else ["-n"])

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            nb_threads=nb_threads,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._bench_src_path,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        benchmark_duration_seconds: int,
        **kwargs,
    ) -> Dict[str, Any]:
        warmup_filtered_str = command_output.strip().split("measurement")[-1]
        measurements_str = warmup_filtered_str.split("average")[0].strip()
        measurements_lst = [int(line.split("total:")[-1]) for line in measurements_str.splitlines()]
        total_ops = sum(measurements_lst)

        result_dict = {
            "duration": benchmark_duration_seconds,
            "global_count": total_ops,
        }

        return result_dict


def willitscale_campaign(
    name: str = "willitscale_campaign",
    benchmark: Optional[WillItScaleBench] = None,
    src_dir: Optional[PathType] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    test_name: Iterable[str] = ("lock1_processes",),
    warmup_iterations: Iterable[int] = (1,),
    cpu_order: Iterable[CpuOrder] = (),
    use_custom_cpu_pinning: Iterable[bool] = (False,),
    nb_threads: Iterable[int] = (1,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Optional[Dict[str, Any]] = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the Will-it-Scale benchmark."""
    variables = {
        "test_name": test_name,
        "warmup_iterations": warmup_iterations,
        "cpu_order": cpu_order,
        "use_custom_cpu_pinning": use_custom_cpu_pinning,
        "nb_threads": nb_threads,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = WillItScaleBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
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
        results_dir=results_dir,
        pretty=pretty,
    )
