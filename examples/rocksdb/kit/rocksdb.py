# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for RocksDB.
See:
- https://rocksdb.org/
- https://github.com/facebook/rocksdb.git
"""

import pathlib
import re
from typing import Any, Dict, Iterable, List

from benchkit.benchmark import (
    Benchmark,
    CommandAttachment,
    CommandWrapper,
    PostRunHook,
    PreRunHook,
)
from benchkit.campaign import CampaignCartesianProduct
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import Constants, CpuOrder, PathType, Pretty


class RocksDBBench(Benchmark):
    """Benchmark object for RocksDB benchmark."""

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
        a_file = bench_src_path / "Makefile"
        if not self.platform.comm.isdir(bench_src_path) and self.platform.comm.isfile(a_file):
            raise ValueError(
                f"Invalid RocksDB source path: {bench_src_path}\n"
                "src_dir argument must be defined manually."
            )
        self._bench_src_path = bench_src_path

        if build_dir is None:
            self._build_dir = self._bench_src_path / f"build-{self.platform.hostname}"
            self._tmpdb_dir = pathlib.Path("/tmp/benchkit_rocksdb_db")
        else:
            self._build_dir = self._bench_src_path / build_dir
            self._tmpdb_dir = self._build_dir / "tmp" / "benchkit_rocksdb_db"

    @property
    def bench_src_path(self):
        return self._bench_src_path

    @staticmethod
    def get_build_var_names():
        return []

    @staticmethod
    def get_run_var_names():
        return [
            "bench_name",
            "nb_iterations",
            "cpu_order",
            "master_thread_core",
            "nb_threads",
            "lock",
            "atomics",
            "use_lse",
        ]

    @staticmethod
    def get_tilt_var_names():
        return [
            "lock",
            "atomics",
            "use_lse",
        ]

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("libbz2-dev"),
            PackageDependency("libgflags-dev"),
            PackageDependency("liblz4-dev"),
            PackageDependency("libsnappy-dev"),
            PackageDependency("libzstd-dev"),
            PackageDependency("zlib1g-dev"),
        ]

    def build_tilt(self, **kwargs) -> None:
        # TODO deprecate this
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs) -> None:
        src_dir = self._bench_src_path
        build_dir = self._build_dir
        db_bench_path = src_dir / "db_bench"

        nb_active_cpus = self.platform.nb_active_cpus()
        parallel_make_str = f" -j {nb_active_cpus} " if nb_active_cpus > 1 else ""

        self.platform.comm.makedirs(path=build_dir, exist_ok=True)

        # Build
        if not self.platform.comm.isfile(db_bench_path):
            self.platform.comm.shell(
                command=f"make{parallel_make_str} release OBJ_DIR={build_dir}",
                current_dir=src_dir,
                output_is_log=True,
            )

        # Create and fill a database to prepare the benchmark
        if not self.platform.comm.isdir(self._tmpdb_dir):
            self.platform.comm.makedirs(path=self._tmpdb_dir, exist_ok=True)
            self.platform.comm.shell(
                command=[
                    "./db_bench",
                    "--threads=1",
                    "--benchmarks=fillseq",
                    f"--db={self._tmpdb_dir}",
                ],
                current_dir=src_dir,
                output_is_log=True,
            )

    def build_bench(self, **kwargs) -> None:
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
        atomics: str | None = None,
        bench_name: str = "readrandom",
        master_thread_core: int | None = None,
        nb_iterations: int = 40000,
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

        # TODO Duplicate with leveldb, need to refactor
        duration_num = (
            f"--duration={benchmark_duration_seconds}"
            if bench_name in ["readrandom", "readmissing", "readhot", "seekrandom"]
            else f"--num={nb_iterations}"
        )
        if bench_name in [
            "fillseq",
            "fillrandom",
            "fillsync",
            "fill100K",
        ]:
            # TODO these benchmarks require different logic for the previously created database
            raise NotImplementedError(
                f'LevelDB benchmark named "{bench_name}" is not currently supported.'
            )
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
        run_variables: Dict[str, Any],
        benchmark_duration_seconds: int,
        **_kwargs,
    ) -> Dict[str, Any]:
        bench_name: str = run_variables["bench_name"]
        for line in command_output.splitlines():
            sline = line.strip()
            if sline.startswith(bench_name):
                number_pattern = r"([0-9]|[.])+"
                m = re.match(
                    pattern=(
                        rf"{bench_name}\s*:\s*"
                        rf"(?P<microspop>{number_pattern})\s+micros/op\s+"
                        rf"(?P<opspsec>{number_pattern})\s+ops/sec\s+"
                        rf"(?P<seconds>{number_pattern})\s+seconds\s+"
                        rf"(?P<ops>{number_pattern})\s+operations\s*;\s+"
                        rf"(?P<mbps>{number_pattern})\s+MB/s\s+"
                        rf"[(](?P<ofleft>[0-9]+) "
                        rf"of (?P<ofright>[0-9]+) found[)]"
                    ),
                    string=sline,
                )

                gd = m.groupdict()
                nb_operations = int(gd["ops"])

                result_dict = {
                    "duration": benchmark_duration_seconds,
                    "global_count": nb_operations,
                    "microseconds/operation": float(gd["microspop"]),
                    "operations/second": float(gd["opspsec"]),
                    "MB/s": float(gd["mbps"]),
                    "ofleft": int(gd["ofleft"]),
                    "ofright": int(gd["ofright"]),
                }

                return result_dict

        raise ValueError(f"Incoherent output from rocksdb, please check output:\n{command_output}")


def rocksdb_campaign(
    name: str = "rocksdb_campaign",
    benchmark: RocksDBBench | None = None,
    bench_name: Iterable[str] = ("readrandom",),
    nb_iterations: Iterable[int] = (40000,),
    src_dir: PathType | None = None,
    build_dir: str | None = None,
    results_dir: PathType | None = None,
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
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Pretty | None = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the RocksDB benchmark."""
    variables = {
        "lock": locks,
        "cpu_order": cpu_order,
        "master_thread_core": master_thread_core,
        "use_lse": use_lse,
        "atomics": atomics,
        "nb_threads": nb_threads,
        "bench_name": bench_name,
        "nb_iterations": nb_iterations,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = RocksDBBench(
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
