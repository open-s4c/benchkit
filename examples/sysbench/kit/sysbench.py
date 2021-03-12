# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for sysbench benchmark.
See: https://github.com/akopytov/sysbench
"""

import os.path
import pathlib
import random
import re
import sys
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from benchkit.benchmark import (
    Benchmark,
    CommandAttachment,
    CommandWrapper,
    PostRunHook,
    PreRunHook,
    RecordResult,
    SharedLib,
)
from benchkit.campaign import CampaignIterateVariables, Constants, Pretty
from benchkit.dependencies.executables import executable_is_installed
from benchkit.dependencies.packages import PackageDependency
from benchkit.helpers.sql import DBMS, SQLClient
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shellasync import shell_async
from benchkit.utils.dir import find_specific_dependency, parentdir
from benchkit.utils.misc import TimeMeasure
from benchkit.utils.types import CpuOrder, PathType, SplitCommand


class Sysbench(Benchmark):
    """
    Benchmark object for sysbench benchmark.
    Interesting source: https://ittutorial.org/how-to-benchmark-performance-of-mysql-using-sysbench/
    """

    def __init__(
        self,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        dbms: DBMS,
        platform: Platform,
        freshdb_foreach_run: bool,
        db_host: str = "127.0.0.1",
        db_port: int = 3306,
        user: str = "sbtest_user",
        password: str = "uu9Mu3sh",
        db_name: str = "sbtest",
        sysbench_src_dir: Optional[PathType] = None,
    ):
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        self.platform = platform  # TODO Warning! overriding upper class platform
        print(
            "[WARNING(dev)] Sysbench: overriding upper class platform; "
            "will be addressed in the future",
            file=sys.stderr,
        )

        self._dbms = dbms

        self._freshdb_foreach_run = freshdb_foreach_run
        self._bench_user = user
        self._bench_password = password
        self._bench_dbname = db_name
        self._db_driver = self._dbms.sysbench_db_driver()
        self._db_host = db_host
        self._db_port = db_port

        # list of possible paths where scripts are located:
        self._lua_script_dirs = []
        if "aarch64" == self.platform.architecture:
            # work around a bug in lua on arm64; TODO check if the bug is still there
            # TODO only support locally
            sysbench_kit_dir = parentdir(path=os.path.realpath(__file__), levels=2)
            lua_script_dir = sysbench_kit_dir / "scripts"
            self._lua_script_dirs += [lua_script_dir]
            self._cd_to_lua = True

        if sysbench_src_dir is None:
            # TODO only supported locally
            self._from_sources = False
            sysbench_kit_dir = parentdir(path=os.path.realpath(__file__), levels=2)
            self._bench_src_path = sysbench_kit_dir
            self._sysbench_bin = "sysbench"
            self._lua_script_dirs += ["/usr/share/sysbench/"]
            if not executable_is_installed(name="sysbench", platform=self.platform):
                raise ValueError(
                    (
                        "sysbench not installed, please install it or "
                        'provide "sysbench_src_dir" to build it from '
                        "sources."
                    )
                )
        else:
            self._from_sources = True
            self._bench_src_path = self.platform.comm.realpath(sysbench_src_dir)
            self._sysbench_bin = self._bench_src_path / "src" / "sysbench"
            self._lua_script_dirs += [self._bench_src_path / "src" / "lua"]
        self._cd_to_lua = False  # TODO?
        self._last_run_info = None

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names():
        return [
            "lock",  # id of the lock
            "mysql_mutex_type",
            "lock_filename",
            "lock_use_bigsmall",
            "lxe",
        ]

    @staticmethod
    def get_run_var_names():
        return [
            "lua_script_filenames",
            "nb_tables",
            "table_size",
            "warmup_seconds",
            "dbms_numa_node_range",
            "dbms_numa_cpu_range",
            "dbms_logging_cores",
            "sysbench_threads",
            "sb_numa_cpu_range",
            "cpu_order",
            "master_thread_core",
            "atomics",
            "use_lse",
        ]

    @staticmethod
    def get_tilt_var_names():  # TODO tilt support
        return [
            "lock",
            "atomics",
            "use_lse",
        ]

    def lua_script_path(self, lua_script_filename: PathType) -> str:
        """
        Return the path to the lua script given its filename.

        Args:
            lua_script_filename (PathType): filename for which to find the path.

        Raises:
            ValueError: if the path is not found.

        Returns:
            str: the path to the lua script given its filename.
        """
        for directory in self._lua_script_dirs:
            path = directory / lua_script_filename
            if self.platform.comm.isfile(path):
                return path
        raise ValueError(
            (
                f'Impossible to find script "{lua_script_filename}" '
                f"in any of the given directories "
                f'({",".join(map(str, self._lua_script_dirs))}).'
            )
        )

    def dependencies(self):
        package_names = ["build-essential"]
        if self._from_sources:
            package_names += [
                "make",
                "automake",
                "libtool",
                "pkg-config",
                "libaio-dev",
                "libmysqlclient-dev",
                "libssl-dev",
                "libpq-dev",
            ]
        else:
            package_names += ["sysbench"]

        return (
            super().dependencies()
            + self._dbms.dependencies()
            + [PackageDependency(name=n, platform=self.platform) for n in package_names]
        )

    def build_tilt(self, **kwargs):
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **kwargs):
        with TimeMeasure() as prebuild_duration:
            if self._from_sources:
                self._build_sysbench()

        prebuild_seconds = prebuild_duration.duration_seconds
        return prebuild_seconds

    def build_bench(
        self,
        **kwargs,
    ):
        """
        Build the benchmark.

        Args:
            benchmark_duration_seconds (_type_): duration of a single run.
        """
        self._dbms.build(**kwargs)

    def clean_bench(self):
        self._dbms.clean()

    def single_run(  # pylint: disable=arguments-differ
        self,
        build_variables: Dict[str, Any],
        record_data_dir: pathlib.Path,
        benchmark_duration_seconds: int,
        lua_script_filenames: List[str] = ("oltp_read_write.lua",),
        nb_tables: int = 16,
        table_size: int = 100,
        warmup_seconds: int = 0,
        dbms_numa_node_range: str | None = None,
        dbms_numa_cpu_range: str | None = None,
        dbms_logging_cores: Tuple[int, int] | None = None,
        sysbench_threads: int = 4,
        sb_numa_cpu_range: str | None = None,
        cpu_order: CpuOrder = None,
        master_thread_core: Optional[int] = None,
        atomics: str | None = None,
        use_lse: bool = False,
        **kwargs,
    ) -> str:
        additional_params = {
            "cpu_order": cpu_order,
            "use_lse": use_lse,
            "atomics": atomics,
        }
        assert additional_params  # TODO migrate this where it is actually used

        main_lua_script_filename = lua_script_filenames[0]

        instance_name = ""
        if not self._freshdb_foreach_run:
            lua_script_noext = os.path.splitext(main_lua_script_filename)[0]
            # Instance name allows to re-use the same data directory for the same lua script,
            # i.e. nb_tables and table_size:
            instance_name = f"instance-sb-{lua_script_noext}-n{nb_tables}-s{table_size}"

        dbms_build_dir = self._dbms.build_dir(**build_variables)  # TODO

        with self._dbms.instance(
            build_dir=dbms_build_dir,
            instance_dirname=instance_name,
            numa_cpu_range=dbms_numa_cpu_range,
            numa_node_range=dbms_numa_node_range,
        ) as dbms_instance:
            if dbms_logging_cores is not None:
                logging_core_1, logging_core_2 = dbms_logging_cores
                raise NotImplementedError("TODO: pin threads on both local & remote comm layer")
                lgc1, lgc2 = logging_core_1, logging_core_2  # pylint: disable=unreachable
                dbms_instance.pin_threads(lgc1, lgc2)

            with TimeMeasure() as dbbuild_duration:
                db_is_built = self._db_is_built(
                    dbms_client=dbms_instance.client,
                    nb_tables=nb_tables,
                    table_size=table_size,
                )
                if self._freshdb_foreach_run or not db_is_built:
                    self._db_build(
                        dbms_client=dbms_instance.client,
                        nb_tables=nb_tables,
                        table_size=table_size,
                        lua_script_filename=main_lua_script_filename,
                    )
                    confirm_built = self._db_is_built(
                        dbms_client=dbms_instance.client,
                        nb_tables=nb_tables,
                        table_size=table_size,
                    )
                    if not confirm_built:
                        raise ValueError("Database not correctly built")

            # Notice the warmup is used twice
            # If not warmup is used, the overall performance of the benchmark is very bad
            print(f"[INFO] Cooldown DBMS for {warmup_seconds}s to give it time to load...")
            time.sleep(warmup_seconds)
            print("[INFO] Cooldown done.")

            # TODO hack
            if "mysql" == self._db_driver:
                # TODO check the following:
                mysqld_process = dbms_instance._mysqld_process  # pylint: disable=protected-access
                for attachment in self._command_attachments:
                    attachment(
                        process=mysqld_process,
                        record_data_dir=None,
                    )

            with TimeMeasure() as bench_duration:
                bench_output = self._run_benchmark(
                    lua_script_filenames=lua_script_filenames,
                    nb_tables=nb_tables,
                    table_size=table_size,
                    sysbench_nb_threads=sysbench_threads,
                    sb_numa_cpu_range=sb_numa_cpu_range,
                    main_warmup_seconds=warmup_seconds,
                    main_duration_seconds=benchmark_duration_seconds,
                    record_data_dir=record_data_dir,
                    cpu_order=cpu_order,
                    master_thread_core=master_thread_core,
                    **kwargs,
                )

                dbms_instance.close(cleanup=self._freshdb_foreach_run)

        self._last_run_info = {
            "dbbuild_seconds": dbbuild_duration.duration_seconds,
            "measured_duration_seconds": bench_duration.duration_seconds,
            "db_driver": self._db_driver,
        }

        return bench_output

    def parse_output_to_results(
        self,
        command_output: str,
        build_variables: Dict[str, Any],
        run_variables: Dict[str, Any],
        benchmark_duration_seconds: int,
        record_data_dir: PathType,
        **kwargs,
    ) -> RecordResult:
        pattern1 = (
            r".*SQL statistics:\s+queries performed:\s+"
            r"read:\s+(?P<nb_queries_read>\d+)\s+"
            r"write:\s+(?P<nb_queries_write>\d+)\s+"
            r"other:\s+(?P<nb_queries_other>\d+)\s+"
            r"total:\s+(?P<nb_queries_total>\d+)\s+"
            r"transactions:\s+(?P<nb_transactions>\d+)\s+[(](?P<tps>\d+[.]\d+) per sec.[)]\s+"
            r"queries:\s+(?P<nb_queries>\d+)\s+[(](?P<qps>\d+[.]\d+) per sec.[)]\s+"
            r"ignored errors:\s+(?P<nb_errors>\d+)\s+[(](?P<eps>\d+[.]\d+) per sec.[)]\s+"
            r"reconnects:\s+(?P<nb_reconnects>\d+)\s+[(](?P<rps>\d+[.]\d+) per sec.[)]\s+"
            r"General statistics:\s+"
            r"total time:\s+(?P<total_time>\d+[.]\d+)s\s+"
            r"total number of events:\s+(?P<total_nb_events>\d+)\s+"
            r"Latency [(]ms[)]:\s+"
            r"min:\s+(?P<latency_ms_min>\d+[.]\d+)\s+"
            r"avg:\s+(?P<latency_ms_avg>\d+[.]\d+)\s+"
            r"max:\s+(?P<latency_ms_max>\d+[.]\d+)\s+"
            r"95th percentile:\s+(?P<latency_ms_95p>\d+[.]\d+)\s+"
            r"sum:\s+(?P<latency_ms_sum>\d+[.]\d+)\s+"
            r"Threads fairness:\s+"
            r"events [(]avg/stddev[)]:\s+"
            r"(?P<fairness_events_avg>\d+[.]\d+)/"
            r"(?P<fairness_events_std>\d+[.]\d+)\s+"
            r"execution time [(]avg/stddev[)]:\s+"
            r"(?P<fairness_executiontime_avg>\d+[.]\d+)/"
            r"(?P<fairness_executiontime_std>\d+[.]\d+)\s+"
            r".*"
        )
        pattern2 = (
            r".*SQL statistics:\s+queries performed:\s+"
            r"read:\s+(?P<nb_queries_read>\d+)\s+"
            r"write:\s+(?P<nb_queries_write>\d+)\s+"
            r"other:\s+(?P<nb_queries_other>\d+)\s+"
            r"total:\s+(?P<nb_queries_total>\d+)\s+"
            r"transactions:\s+(?P<nb_transactions>\d+)\s+[(](?P<tps>\d+[.]\d+) per sec.[)]\s+"
            r"queries:\s+(?P<nb_queries>\d+)\s+[(](?P<qps>\d+[.]\d+) per sec.[)]\s+"
            r"ignored errors:\s+(?P<nb_errors>\d+)\s+[(](?P<eps>\d+[.]\d+) per sec.[)]\s+"
            r"reconnects:\s+(?P<nb_reconnects>\d+)\s+[(](?P<rps>\d+[.]\d+) per sec.[)]\s+"
            r"Throughput:\s+"
            r"events/s [(]eps[)]:\s+(?P<events_per_s>\d+[.]\d+)\s+"
            r"time elapsed:\s+(?P<time_elapsed_s>\d+[.]\d+)s\s+"
            r"total number of events:\s+(?P<total_nb_events>\d+)\s+"
            r"Latency [(]ms[)]:\s+"
            r"min:\s+(?P<latency_ms_min>\d+[.]\d+)\s+"
            r"avg:\s+(?P<latency_ms_avg>\d+[.]\d+)\s+"
            r"max:\s+(?P<latency_ms_max>\d+[.]\d+)\s+"
            r"95th percentile:\s+(?P<latency_ms_95p>\d+[.]\d+)\s+"
            r"sum:\s+(?P<latency_ms_sum>\d+[.]\d+)\s+"
            r"Threads fairness:\s+"
            r"events [(]avg/stddev[)]:\s+"
            r"(?P<fairness_events_avg>\d+[.]\d+)/"
            r"(?P<fairness_events_std>\d+[.]\d+)\s+"
            r"execution time [(]avg/stddev[)]:\s+"
            r"(?P<fairness_executiontime_avg>\d+[.]\d+)/"
            r"(?P<fairness_executiontime_std>\d+[.]\d+)\s+"
            r".*"
        )
        patterns = [pattern1, pattern2]

        # Ensures only the latest reported statistics are used (discarding warmups):
        last_output = command_output[command_output.rfind("SQL statistics:") :]
        matches = [
            m
            for p in patterns
            if (
                m := re.match(
                    pattern=p,
                    string=last_output,
                    flags=re.MULTILINE | re.DOTALL,
                )
            )
            is not None
        ]

        if not matches:
            raise ValueError("Cannot parse sysbench output")
        m = matches[0]

        gd = m.groupdict()

        result_dict = {}
        result_dict |= self._last_run_info
        result_dict |= gd

        if "nb_threads" not in result_dict:
            result_dict["nb_threads"] = run_variables["sysbench_threads"]

        return result_dict

    def _build_sysbench(self):
        def run(cmd: str):
            self.platform.comm.shell(
                command=cmd,
                current_dir=self.bench_src_path,
                output_is_log=True,
            )

        if not self.platform.comm.isfile(self.bench_src_path / "Makefile"):
            run("./autogen.sh")
            run("./configure --with-mysql --with-pgsql")

        run("make -j")

        assert self.platform.comm.isfile(self._sysbench_bin)

    def _db_is_built(
        self,
        dbms_client: SQLClient,
        nb_tables: int = 16,
        table_size: int = 100,
    ) -> bool:
        users = dbms_client.list_users()
        if self._bench_user not in users:
            return False
        databases = dbms_client.list_databases()
        if self._bench_dbname not in databases:
            return False

        table_names = dbms_client.list_tables(database_name=self._bench_dbname)
        if len(table_names) != nb_tables:
            return False

        tables = dbms_client.list_tables_info(
            database_name=self._bench_dbname,
            fields=["nb_rows"],
        )
        for i in range(1, nb_tables + 1):
            expected_table_name = f"sbtest{i}"
            if expected_table_name not in tables:
                return False

            actual_table = tables[expected_table_name]
            if expected_table_name != actual_table["name"]:
                return False
            if actual_table["nb_rows"] < 0:
                return False  # InnoDB 'TABLE_ROWS' field is a rough estimate

        # we only randomly check 5 tables sizes if there are more than 15 tables
        tables_to_check = table_names if len(tables) <= 15 else random.sample(table_names, 5)

        for actual_table in tables_to_check:
            actual_length = dbms_client.table_length(
                database_name=self._bench_dbname,
                table_name=actual_table,
            )
            if table_size != actual_length:
                print(
                    f"[ERROR] Table {actual_table} has {actual_length} rows. "
                    "Expected: {table_size} rows.",
                    file=sys.stderr,
                )
                return False

        return True

    def _db_build(
        self,
        dbms_client: SQLClient,
        nb_tables: int,
        table_size: int,
        lua_script_filename: PathType,
    ) -> None:
        # create user & db for the benchmark
        bench_user = self._bench_user
        dbms_client.create_user(user=bench_user, password=self._bench_password)
        dbms_client.create_database(name=self._bench_dbname)
        dbms_client.grant_privileges(user=bench_user)

        script_path = self.lua_script_path(lua_script_filename=lua_script_filename)
        cwd = parentdir(script_path) if self._cd_to_lua else self._bench_src_path

        self.platform.comm.shell(
            command=f"{self._sysbench_bin} --version",
            current_dir=cwd,
            output_is_log=True,
        )

        # number of threads to build the db, not to execute the benchmark!
        nb_threads = min(10, self.platform.nb_active_cpus())
        # TODO warning, does not support cpuisol
        numactl = ["numactl", "--all", "-C", f"0-{nb_threads-1}"]  # TODO

        # start build of database according to Sysbench
        sysbench_cmd = [
            f"{self._sysbench_bin}",
            "--debug=off",
            # TODO? '--report-interval=10',
            f"--db-driver={self._db_driver}",
            f"--{self._db_driver}-user={self._bench_user}",
            f"--{self._db_driver}-password={self._bench_password}",
            f"--{self._db_driver}-db={self._bench_dbname}",
            f"--{self._db_driver}-host={self._db_host}",
            f"--{self._db_driver}-port={self._db_port}",
            f"--tables={nb_tables}",
            f"--table-size={table_size}",
            f"--threads={nb_threads}",
            "--db-ps-mode=disable",
            f"{script_path}",
            "prepare",
        ]

        cmd = numactl + sysbench_cmd

        self.platform.comm.shell(
            command=cmd,
            current_dir=cwd,
            output_is_log=True,
        )

    def _run_benchmark(
        self,
        lua_script_filenames: List[str],
        nb_tables: int,
        table_size: int,
        sysbench_nb_threads: int,
        sb_numa_cpu_range: str | None,
        main_warmup_seconds: int,
        main_duration_seconds: int,
        record_data_dir: pathlib.Path,
        cpu_order: CpuOrder = None,
        master_thread_core: Optional[int] = None,
        **kwargs,
    ):
        def get_sysbench_cmd(
            lua_script_filename: str,
            warmup_seconds: int,
            duration_seconds: int,
        ) -> SplitCommand:
            script_path = self.lua_script_path(lua_script_filename=lua_script_filename)

            sysbench_cmd = [
                f"{self._sysbench_bin}",
                "--debug=off",
                f"--db-driver={self._db_driver}",
                f"--{self._db_driver}-user={self._bench_user}",
                f"--{self._db_driver}-password={self._bench_password}",
                f"--{self._db_driver}-db={self._bench_dbname}",
                f"--{self._db_driver}-host={self._db_host}",
                f"--{self._db_driver}-port={self._db_port}",
                f"--tables={nb_tables}",
                f"--table-size={table_size}",
                f"--threads={sysbench_nb_threads}",
                f"--time={duration_seconds + warmup_seconds}",  # 'time' is the total duration
                f"--report-checkpoints={warmup_seconds}",
                "--db-ps-mode=disable",
                # TODO? f'--events=0',
                # TODO? '--max-requests=0',
                "--forced-shutdown=off",  # or f'--forced-shutdown={duration_seconds}'
                "--report-interval=1",
                "--histogram=on",
                f"{script_path}",
                "run",
            ]
            return sysbench_cmd

        # TODO one numactl per sysbench bench?
        numactl = (
            ["numactl", "--all", "-C", f"{sb_numa_cpu_range}"]
            if sb_numa_cpu_range is not None
            else []
        )

        main_sysbench_cmd = get_sysbench_cmd(
            lua_script_filename=lua_script_filenames[0],
            warmup_seconds=main_warmup_seconds,
            duration_seconds=main_duration_seconds,
        )
        auxiliary_sysbench_script_cmds = [
            (
                lsf,
                get_sysbench_cmd(
                    lua_script_filename=lsf,
                    warmup_seconds=0,
                    duration_seconds=0,
                ),
            )
            for lsf in lua_script_filenames[1:]
        ]

        flamegraph = False  # TODO
        if flamegraph:
            self._flamegraph_path = "../deps/FlameGraph"  # TODO appropriate handling of the path
            # TODO: prepend the flamegraph or use the command wrapper.

        auxiliary_processes = [
            shell_async(
                command=numactl + auxiliary_sysbench_cmd,
                stdout_path=record_data_dir / f"aux-{i:03}-{lua_script_fn}.out",
                stderr_path=record_data_dir / f"aux-{i:03}-{lua_script_fn}.err",
                platform=self.platform,
                current_dir=self.bench_src_path,
            )
            for i, (lua_script_fn, auxiliary_sysbench_cmd) in enumerate(
                auxiliary_sysbench_script_cmds,
                start=1,
            )
        ]

        run_command = numactl + main_sysbench_cmd

        environment = self._preload_env(
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
        )
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
            print_output=True,
        )

        for process in auxiliary_processes:
            process.stop()

        return output


def _find_sysbench_src_path(platform: Platform) -> pathlib.Path:
    sysbench_src_path = find_specific_dependency("sysbench")
    assert platform.comm.path_exists(sysbench_src_path / "autogen.sh")
    return sysbench_src_path


def sysbench_campaign(
    name: str,
    dbms: DBMS,
    client_platform: Platform | None = None,
    db_host: str = "127.0.0.1",
    db_port: int = 3306,
    benchmark: Optional[Sysbench] = None,
    sysbench_src_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    freshdb_foreach_run: bool = False,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    bench_variables: Iterable[Dict[str, Any]] = (),
    constants: Constants = None,
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    results_dir: Optional[PathType] = None,
    pretty: Optional[Pretty] = None,
) -> CampaignIterateVariables:
    """Return a cartesian product campaign configured for the sysbench benchmark."""
    if client_platform is None:
        client_platform = get_current_platform()

    if pretty is not None:
        pretty = {"lock": pretty}

    if sysbench_src_dir is None:
        sysbench_src_dir = _find_sysbench_src_path(platform=client_platform)

    if not isinstance(benchmark, Sysbench):
        benchmark = Sysbench(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            dbms=dbms,
            platform=client_platform,
            freshdb_foreach_run=freshdb_foreach_run,
            db_host=db_host,
            db_port=db_port,
            sysbench_src_dir=sysbench_src_dir,
        )

    return CampaignIterateVariables(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=bench_variables,
        constants=constants,
        debug=debug,
        gdb=gdb,
        enable_data_dir=enable_data_dir,
        continuing=continuing,
        benchmark_duration_seconds=benchmark_duration_seconds,
        results_dir=results_dir,
        pretty=pretty,
    )
