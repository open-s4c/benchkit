# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType


class NPBBench(Benchmark):
    """
    Benchmark object for Will-it-Scale benchmark.
    """

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
        readme_file = bench_src_path / "README"
        if not all(
            [
                self.platform.comm.isdir(bench_src_path),
                self.platform.comm.isfile(readme_file),
            ]
        ):
            raise ValueError(
                f"Invalid NAS parallel benchmark source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )

        if not (omp_dirs := list(bench_src_path.glob("NPB*-OMP"))):
            raise ValueError("Cannot find NPB-OMP parallel benchmark source")

        omp_dir = omp_dirs[0]
        npb_version = re.match(pattern=r"NPB(\d+\.\d+)-", string=omp_dir.name).group(1)

        self._bench_src_path = bench_src_path
        self._bench_mpi_path = bench_src_path / f"NPB{npb_version}-MPI"
        self._bench_omp_path = bench_src_path / f"NPB{npb_version}-OMP"
        self._npb_version = npb_version

    @property
    def bench_src_path(self) -> str:
        return str(self._bench_src_path)

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            "category",  # either "MPI" or "OMP"
            "test_name",
            "t_class",
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "cpu_order",
            "master_thread_core",
            "nb_threads",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("libhwloc-dev"),
            PackageDependency("gfortran"),
        ]

    def build_tilt(self, **kwargs) -> None:
        raise NotImplementedError("Tilt is not necessary for this benchmark.")

    def prebuild_bench(
        self,
        **_kwargs,
    ) -> None:
        pass

    def build_bench(  # pylint: disable=arguments-differ
        self,
        category: str = "OMP",
        test_name: str = "lu",
        t_class: str = "A",
        **_kwargs,
    ) -> None:
        src_dir = self._get_actual_src_dir(category=category)

        config_dir = src_dir / "config"
        config_tpl_file = config_dir / "make.def.template"
        config_file = config_dir / "make.def"
        config_content = self.platform.comm.read_file(path=config_tpl_file)
        self.platform.comm.write_content_to_file(
            content=config_content,
            output_filename=config_file,
        )

        self.platform.comm.makedirs(path=src_dir/"bin", exist_ok=True)

        self.platform.comm.shell(
            command=f"make {test_name} CLASS={t_class}",
            current_dir=src_dir,
            print_input=True,
            print_output=True,
        )

    def clean_bench(self) -> None:
        for src_dir in [self._bench_mpi_path, self._bench_omp_path]:
            self.platform.comm.shell(command="make clean", current_dir=src_dir)

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        build_variables: Dict[str, Any],
        cpu_order: CpuOrder = None,
        nb_threads: int = 2,
        master_thread_core: Optional[int] = None,
        **kwargs,
    ) -> str:
        # TODO manage the defaults at framework level:
        category: str = build_variables["category"] if "category" in build_variables else "OMP"
        test_name: str = build_variables["test_name"]
        t_class: str = build_variables["t_class"]

        src_dir = self._get_actual_src_dir(category=category)

        environment = self._preload_env(
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            **kwargs,
        )
        if environment is None:
            environment = {}

        environment["OMP_NUM_THREADS"] = str(nb_threads)
        run_command = [f"./bin/{test_name}.{t_class}.x"]

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
            current_dir=src_dir,
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

        total_time = command_output.strip().split("seconds =")[1].split("\n")[0].strip()
        mops_total = command_output.strip().split("Mop/s total     =")[1].split("\n")[0].strip()
        mops_thread = command_output.strip().split("Mop/s/thread    =")[1].split("\n")[0].strip()

        result_dict = {
            "duration": total_time,
            "throughput": mops_total,
            "throughput_thread": mops_thread,
        }

        return result_dict

    def _get_actual_src_dir(self, category: str) -> PathType:
        match category:
            case "MPI":
                src_dir = self._bench_mpi_path
            case "OMP":
                src_dir = self._bench_omp_path
            case _:
                raise ValueError(f"Invalid npb benchmark category: {category}")

        return src_dir


def npb_campaign(
    name: str = "npb_campaign",
    benchmark: Optional[NPBBench] = None,
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
    test_name: Iterable[str] = ("mg",),
    t_class: Iterable[str] = ("C",),
    cpu_order: Iterable[CpuOrder] = (),
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
        "t_class": t_class,
        "cpu_order": cpu_order,
        "nb_threads": nb_threads,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = NPBBench(
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
