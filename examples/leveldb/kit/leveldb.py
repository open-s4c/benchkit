# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for LevelDB benchmark.
See: https://github.com/google/leveldb
"""

import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType


class LevelDBBench(Benchmark):
    """Benchmark object for LevelDB benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
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
            bench_src_path / "benchmarks/db_bench.cc"
        ):
            raise ValueError(
                f"Invalid LevelDB source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path

        if build_dir is None:
            self._build_dir = self._bench_src_path / f"build-{self.platform.hostname}"
            self._tmpdb_dir = "/tmp/benchkit_leveldb_db"
        else:
            self._build_dir = self._bench_src_path / build_dir
            self._tmpdb_dir = self._build_dir / "tmp" / "benchkit_leveldb_db"

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "bench_name",
            "cpu_order",
            "master_thread_core",
            "nb_threads",
            "lock",
            "atomics",
            "use_lse",
            "freshdb_foreach_run",
            "num",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return [
            "lock",
            "atomics",
            "use_lse",
        ]

    @staticmethod
    def _parse_results(
        output: str,
        nb_threads: int,
    ) -> Dict[str, str]:
        benchstats = output.split("benchstats:")[-1].strip()
        values = benchstats.split(";")

        if len(values) != nb_threads + 2:
            raise ValueError(f"Incoherent output from leveldb, please check output:\n {output}")

        names = ["duration", "global_count"] + [f"thread_{k}" for k in range(nb_threads)]
        result_dict = dict(zip(names, values))

        computed_duration = float(result_dict.get("duration")) / nb_threads
        result_dict["duration"] = str(computed_duration)

        return result_dict

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("cmake"),
        ]

    def build_tilt(self, **kwargs) -> None:
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs) -> None:
        build_dir = self._build_dir
        self.platform.comm.makedirs(path=build_dir, exist_ok=True)

        must_debug = self.must_debug()
        cmake_build_type = "Debug" if must_debug else "Release"

        self.platform.comm.shell(
            command=f"cmake -DCMAKE_BUILD_TYPE={cmake_build_type} {self._bench_src_path}",
            current_dir=build_dir,
            output_is_log=True,
        )
        self.platform.comm.shell(
            command=f"make{self._parallel_make_str()} db_bench",
            current_dir=build_dir,
            output_is_log=True,
        )
        if not self.platform.comm.isdir(self._tmpdb_dir):
            self.platform.comm.makedirs(path=self._tmpdb_dir, exist_ok=True)
            db_init_command = [
                "./db_bench",
                "--threads=1",
                "--benchmarks=fillseq",
                f"--db={self._tmpdb_dir}",
            ]
            self.platform.comm.shell(command=db_init_command, current_dir=build_dir)

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
        lock: str = "",
        nb_threads: int = 2,
        cpu_order: CpuOrder = None,
        use_lse: bool = False,
        atomics: Optional[str] = None,
        bench_name: str = "readrandom",
        master_thread_core: Optional[int] = None,
        num: int = 1000000,
        freshdb_foreach_run: bool = False,
        **kwargs,
    ) -> str:
        if freshdb_foreach_run:
            db_init_command = [
                "./db_bench",
                "--threads=1",
                "--benchmarks=fillseq",
                f"--db={self._tmpdb_dir}",
            ]
            self.platform.comm.shell(
                command=db_init_command,
                current_dir=self._build_dir,
                print_output=False
            )

        environment = self._preload_env(
            lock=lock,
            use_lse=use_lse,
            atomics=atomics,
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            **kwargs,
        )

        if bench_name in ["readrandom", "readmissing", "readhot", "seekrandom"]:
            duration_num = f"--duration={benchmark_duration_seconds}"
        else:
            duration_num = f"--num={num // nb_threads}"


        if bench_name in [
            "fillseq",
            "fillrandom",
            "fillsync",
            "fill100K",
        ]:
            use_existing_db = False
        else:
            use_existing_db = True


        run_command = [
            "./db_bench",
            f"--threads={nb_threads}",
            f"--benchmarks={bench_name}",
            f'--use_existing_db={"1" if use_existing_db else "0"}',
            f"--db={self._tmpdb_dir}",
            duration_num,
        ]
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
        nb_threads = int(run_variables["nb_threads"])
        result_dict = self._parse_results(output=command_output, nb_threads=nb_threads)
        return result_dict


def leveldb_campaign(
    name: str = "leveldb_campaign",
    benchmark: Optional[LevelDBBench] = None,
    bench_name: Iterable[str] = ("readrandom",),
    src_dir: Optional[PathType] = None,
    build_dir: Optional[str] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    locks: Iterable[str] = (),
    cpu_order: Iterable[CpuOrder] = (),
    master_thread_core: Iterable[int | None] = (),
    use_lse: Iterable[bool] = (),
    atomics: Iterable[str] = (),
    nb_threads: Iterable[int] = (1,),
    num: Iterable[int] = (1000000,),
    freshdb_foreach_run: Iterable[bool] = (False,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the LevelDB benchmark."""
    variables = {
        "lock": locks,
        "cpu_order": cpu_order,
        "master_thread_core": master_thread_core,
        "use_lse": use_lse,
        "atomics": atomics,
        "nb_threads": nb_threads,
        "bench_name": bench_name,
        "freshdb_foreach_run": freshdb_foreach_run,
        "num": num,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = LevelDBBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
            build_dir=build_dir,
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
