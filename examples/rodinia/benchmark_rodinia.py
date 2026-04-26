# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, CampaignIterateVariables, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType

supported_bench_names = [
    "bfs",
    "heartwall",
    "lud",
    "needle",
    "srad",
]


class RodiniaBench(Benchmark):
    """Benchmark object for Rodinia benchmarks."""

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
                f"Invalid Rodinia source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            "bench_name",
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "bench_name",
            "nb_threads",
            "size",
        ]

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            # PackageDependency("openjdk-21-jdk"),
        ]

    def prebuild_bench(self, **_kwargs) -> None:
        pass

    def build_bench(
        self,
        bench_name: str,
        **kwargs,
    ) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        size: Any,
        nb_threads: int,
        bench_name: str,
        **kwargs,
    ) -> str:

        environment = {"OMP_NUM_THREADS": str(nb_threads)}

        if bench_name == "needle":
            bench_dir = self._bench_src_path / "nw"
        elif bench_name == "srad":
            bench_dir = self._bench_src_path / "srad_v2"
        else:
            bench_dir = self._bench_src_path / bench_name

        run_command = [f"./{bench_name}"]

        match bench_name:
            case "bfs":
                run_command.append(f"../../data/bfs/inputGen/graph{size}.txt")
            case "heartwall":
                run_command.extend(["../../data/heartwall/test.avi", str(size)])
            case "lud":
                run_command.extend(["-n", str(nb_threads), "-i", f"../../data/lud/{size}.dat"])
            case "needle":
                run_command.extend([str(size), "10", str(nb_threads)])
            case "srad":
                run_command.extend(
                    ["2048", "2048", "0", "127", "0", "127", str(nb_threads), "0.5", str(size)]
                )  # TODO: might change another argument as size
            case _:
                raise RuntimeWarning("Unkown bench_name")

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=bench_dir,
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
        return {}


def rodinia_campaign(
    name: str = "rodinia_campaign",
    benchmark: Optional[RodiniaBench] = None,
    bench_names: Iterable[str] = ("bfs",),
    src_dir: Optional[PathType] = None,
    # build_dir: Optional[str] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    variables: Iterable[dict[str, Any]] = [],
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
    symlink_latest: bool = False,
) -> CampaignIterateVariables:
    """Return a campaign configured for the Rodinia benchmark."""

    if not all(bench_name in supported_bench_names for bench_name in bench_names):
        unsupported_benchmarks = [
            bench_name for bench_name in bench_names if bench_name not in supported_bench_names
        ]
        raise ValueError(
            f"Invalid bench_names for Rodinia: {unsupported_benchmarks}\n"
            f"The supported bench names are: {supported_bench_names}."
        )

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = RodiniaBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
        )

    return CampaignIterateVariables(
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
        symlink_latest=symlink_latest,
    )
