# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for benchmarksql benchmark.
See:
- https://benchmarksql.readthedocs.io/en/latest/
- https://github.com/pingcap/benchmarksql
- https://github.com/pgsql-io/benchmarksql/ (the one used to test this benchmark)

TODO this module must be refactored and re-tested.
"""

import datetime
import os
import pathlib
from typing import Any, Dict, Iterable, Optional, Union

from benchkit.benchmark import Benchmark
from benchkit.campaign import CampaignCartesianProduct
from benchkit.dependencies.packages import DockerDependency, PackageDependency
from benchkit.helpers.sql import DBMS, SQLClient
from benchkit.utils import parselog
from benchkit.utils.types import CpuOrder, PathType

from .config import get_mariadb_config


class BenchmarkSQL(Benchmark):
    """Benchmark object for benchmarksql benchmark."""

    def __init__(
        self,
        dbms: DBMS,
        tilt,
        repo_path,
        user: str = "benchmarksql",
        password: str = "PWbmsql",
        db_name: str = "benchmarksql1",
        renew_instance: bool = True,
    ):
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            pre_run_hooks=(),
            shared_libs=[tilt],
            post_run_hooks=(),
        )

        self._dbms = dbms

        self._bench_src_path = pathlib.Path(repo_path)
        self._run_path = self._bench_src_path / "target/run"
        self._build_instance_path = self._bench_src_path / "db_build"
        os.makedirs(self._build_instance_path, exist_ok=True)

        self._bench_configfilename = "benchmarksql.properties"
        self._bench_configpath = (self._build_instance_path / self._bench_configfilename).resolve()

        self._bench_user = user
        self._bench_password = password
        self._bench_dbname = db_name
        self._bench_renew_instance = renew_instance

        if not self._bench_renew_instance:
            self._create_bench_config_file(config_path=self._bench_configpath)

        self._last_run_info = None

    @property
    def bench_src_path(self):
        return self._bench_src_path

    @staticmethod
    def get_build_var_names():
        # TODO choose right parameters for this benchmark
        return [
            "lock",
        ]

    @staticmethod
    def get_run_var_names():
        # TODO choose right parameters for this benchmark
        return [
            "bench_name",
            "cpu_order",
            "master_thread_core",
            "nb_threads",
            "atomics",
            "use_lse",
        ]

    @staticmethod
    def get_tilt_var_names():
        # TODO choose right parameters for this benchmark
        return [
            "lock",
            "atomics",
            "use_lse",
        ]

    def dependencies(self):
        return (
            super().dependencies()
            + self._dbms.dependencies()
            + [
                PackageDependency("build-essential"),
                PackageDependency("openjdk-8-jdk"),
                PackageDependency("openjdk-11-jdk"),
                PackageDependency("maven"),
                DockerDependency(),
            ]
        )

    def build_tilt(self, **kwargs):
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs):
        pass

    def build_bench(
        self,
        **kwargs,
    ) -> float:
        tz = datetime.timezone.utc
        start_time = datetime.datetime.now(tz=tz)

        self._dbms.build(**kwargs)

        self.platform.comm.shell(
            command="mvn",
            current_dir=self._bench_src_path,
            output_is_log=True,
        )

        if not self._bench_renew_instance:
            with self._dbms.instance(instance_dir=self._build_instance_path) as build_db:
                build_db_client = build_db.client
                if self._bench_dbname not in build_db_client.list_databases():
                    self._db_build(dbms_client=build_db_client, config_path=self._bench_configpath)

        prebuild_seconds = (datetime.datetime.now(tz=tz) - start_time).total_seconds()

        return prebuild_seconds

    def clean_bench(self):
        self._dbms.clean()

    def single_run(  # pylint: disable=arguments-differ
        self,
        nb_threads,  # pylint: disable=unused-argument
        cpu_order: CpuOrder,
        use_lse,
        atomics,
        benchmark_duration_seconds,  # pylint: disable=unused-argument
        build_variables,
        lock=None,
        master_thread_core=None,  # pylint: disable=unused-argument
        **_kwargs,
    ):
        fresh_db_build = self._bench_renew_instance
        data_cloned_from = "" if fresh_db_build else self._build_instance_path

        # TODO duplicate
        additional_params = {
            "cpu_order": cpu_order,
            "use_lse": use_lse,
            "atomics": atomics,
        }
        if lock is not None:
            additional_params["lock"] = lock
        elif "lock" in build_variables:
            additional_params["lock"] = build_variables["lock"]
        with self._dbms.instance(
            data_cloned_from=data_cloned_from,
            additional_parameters=additional_params,
        ) as dbms_instance:
            db_build_seconds = 0

            if fresh_db_build:
                config_path = dbms_instance.storage_dir / self._bench_configfilename
                self._create_bench_config_file(config_path=config_path)
            else:
                config_path = self._bench_configpath

            if fresh_db_build:
                db_build_seconds = self._db_build(
                    dbms_client=dbms_instance.client,
                    config_path=config_path,
                )

            bench_seconds = self._run_benchmark(config_path=config_path)
            total_seconds = db_build_seconds + bench_seconds

            self._last_run_info = {
                "db_build_seconds": db_build_seconds,
                "bench_seconds": bench_seconds,
                "total_seconds": total_seconds,
            }

        return ""  # useful output is in log file

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}
        result_dict |= self._last_run_info

        result_dir = self._run_path
        benchlog_path = result_dir / "benchmark.log"

        raw_output_lines = parselog.loglines_common_str(
            log_filename=benchlog_path,
            common_str="[main] result,",
        )
        j = len(raw_output_lines) - 1
        while j >= 0 and "latency (seconds)" not in raw_output_lines[j].strip():
            j -= 1
        if j < 0:
            raise ValueError(f'Malformed benchmark output, no result found in "{benchlog_path}"')
        output_block = raw_output_lines[j:]

        def find_overall_stat(stat: str) -> str:
            stat_lines = [
                line.split(f"Overall {stat}:")[-1].strip()
                for line in output_block
                if " Overall " in line and stat in line
            ]
            assert 1 == len(stat_lines)
            return stat_lines[0]

        nopm_line = find_overall_stat("NOPM")
        nopm_split = nopm_line.split()
        overall_nopm = int(nopm_split[0].replace(",", ""))
        nopm_thmax_ratio = nopm_split[1].replace("(", "").replace("%", "")

        tpm_line = find_overall_stat("TPM")
        overall_tpm = int(tpm_line.replace(",", ""))

        result_dict.update(
            {
                "overall_nopm": overall_nopm,
                "nopm_thmax_ratio": nopm_thmax_ratio,
                "overall_tpm": overall_tpm,
            }
        )

        return result_dict

    def _create_bench_config_file(self, config_path: PathType):
        with open(config_path, "w") as benchmark_configfile:
            bench_config = get_mariadb_config(
                user=self._bench_user,
                password=self._bench_password,
                db_name=self._bench_dbname,
            )
            benchmark_configfile.writelines([f"{line}\n" for line in bench_config])

    def _db_build(
        self,
        dbms_client: SQLClient,
        config_path: PathType,
    ):
        start_time = datetime.datetime.now(tz=datetime.timezone.utc)

        # create user & db for the benchmark
        bench_user = self._bench_user
        dbms_client.create_user(user=bench_user, password=self._bench_password)
        dbms_client.grant_privileges(user=bench_user)
        dbms_client.create_database(name=self._bench_dbname)

        # start build of database according to BenchmarkSQL
        self.platform.comm.shell(
            command=f"./runDatabaseBuild.sh {config_path}",
            current_dir=self._run_path,
            output_is_log=True,
        )

        end_time = datetime.datetime.now(tz=datetime.timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()
        return duration_seconds

    def _run_benchmark(self, config_path: PathType):
        start_time = datetime.datetime.now(tz=datetime.timezone.utc)
        self.platform.comm.shell(
            command=f"./runBenchmark.sh {config_path}",
            current_dir=self._run_path,
            output_is_log=True,
        )
        end_time = datetime.datetime.now(tz=datetime.timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()
        return duration_seconds


def benchmarksql_benchmark(
    benchmarksql_dir: PathType,
    dbms: DBMS,
) -> BenchmarkSQL:
    """
    Get a benchmarksql benchmark instance.

    Args:
        benchmarksql_dir (PathType): path to the directory of the benchmarsql source code.
        dbms (DBMS): DBMS to attach to the benchmark.

    Returns:
        BenchmarkSQL: a benchmarksql benchmark instance.
    """
    return BenchmarkSQL(
        dbms=dbms,
        tilt=None,
        repo_path=benchmarksql_dir,
    )


def benchmarksql_campaign(
    name: str,
    benchmark: Union[BenchmarkSQL, os.PathLike, str],
    dbms: DBMS,
    nb_runs: int,
    locks: Iterable[str],
    cpu_order: CpuOrder,
    nb_threads: Iterable[int],
    use_lse: Iterable[bool],
    atomics: Iterable[str],
    pretty: Optional[Dict[str, str]] = None,
    continuing: bool = False,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the benchmarksql benchmark."""
    variables = {
        "lock": locks,
        "cpu_order": cpu_order,
        "nb_threads": nb_threads,
        "use_lse": use_lse,
        "atomics": atomics,
    }
    if pretty is not None:
        pretty = {"lock": pretty}

    if not isinstance(benchmark, BenchmarkSQL):
        benchmark = benchmarksql_benchmark(benchmarksql_dir=benchmark, dbms=dbms)

    return CampaignCartesianProduct(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=False,
        continuing=continuing,
        pretty=pretty,
    )
