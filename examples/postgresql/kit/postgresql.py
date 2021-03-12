# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for PostgreSQL benchmark.
See https://www.postgresql.org/
"""

import getpass
import os
import pathlib
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from benchkit.commandwrappers.numactl import numactl_cmd_prefix
from benchkit.dependencies.dependency import Dependency
from benchkit.dependencies.packages import PackageDependency
from benchkit.helpers.sql import DBMS, DBMSInstance, SQLClient
from benchkit.platforms import Platform
from benchkit.shell.shellasync import shell_async
from benchkit.utils.types import Command, PathType

_DEFAULT_DATABASE = "postgres"


def _config_str2dict(config_content: str) -> Dict[str, str]:
    def process_line(line: str) -> Tuple[str, str]:
        line2 = line.rsplit(sep="#", maxsplit=1)[0] if "#" in line else line
        line3 = line2.strip()
        key, value = line3.split("=")
        return key, value

    result = dict([process_line(line) for line in config_content.splitlines() if "=" in line])
    return result


def _config_dict2str(config_dict: Dict[str, str]) -> str:
    result = "\n".join([f"{k.strip()} = {v.strip()}" for k, v in config_dict.items()])
    return result


class PostgreSQLClient(SQLClient):
    """Benchmark object for the client in PostgreSQL's benchmark."""

    def __init__(
        self,
        platform: Platform,
        user: str,
        build_dir: pathlib.Path,
    ):
        super().__init__(platform=platform)
        self._user = user
        self._build_dir = build_dir
        self._psql_bin = self._build_dir / "tmp_install/usr/local/pgsql/bin/psql"
        self._libpq = self._build_dir / "src/interfaces/libpq"

    def ping(self) -> bool:  # TODO push up
        return_code = 0
        try:
            self.ping_no_fail()
        except subprocess.CalledProcessError as err:
            return_code = err.returncode
        return return_code == 0

    def ping_no_fail(self) -> None:
        """
        Ping the server, but does not allow the ping to fail.
        Raises an exception if it is the case.
        """
        result = self._psql_cmd(
            command="SELECT datname FROM pg_database;",
            print_info=False,
        )  # try a dummy command

        if not result.startswith("datname"):
            raise ValueError("Cannot parse datname from psql output")

    def shutdown(self) -> None:
        raise NotImplementedError()  # no known way to shut down pgsql from psql client

    def create_user(
        self,
        user: str,
        password: str,
    ) -> str:
        return self._psql_cmd(command=f"CREATE USER {user} WITH PASSWORD '{password}'")

    def grant_privileges(
        self,
        user: str,
    ) -> None:
        databases = self.list_databases()
        databases.remove("template0")
        databases.remove("template1")

        for database in databases:
            out = self._psql_cmd(
                command=f"GRANT ALL PRIVILEGES ON SCHEMA public TO {user}",
                database=database,
            ).strip()
            if "GRANT" != out:
                raise ValueError(f"Cannot grant all privileges on schema public to user {user}")

            out = self._psql_cmd(
                command=f"GRANT ALL PRIVILEGES ON DATABASE {database} TO {user}",
                database=database,
            ).strip()
            if "GRANT" != out:
                raise ValueError(
                    f"Cannot grant all privileges on database '{database}' schema "
                    "public to user '{user}'"
                )

    def create_database(
        self,
        name: str,
    ) -> str:
        return self._psql_cmd(command=f"CREATE DATABASE {name}")

    def list_databases(self) -> List[str]:
        databases = self._postgresql_list(command="SELECT datname FROM pg_database;")
        return databases

    def list_users(self) -> List[str]:
        users = self._postgresql_list(command="SELECT usename FROM pg_user")
        return users

    def list_tables(
        self,
        database_name: str,
    ) -> List[str]:
        tables = self._postgresql_list(
            command="SELECT tablename FROM pg_tables WHERE schemaname = 'public'",
            database=database_name,
        )
        return tables

    def list_tables_info(
        self,
        database_name: str,
        fields: Iterable[str],
    ) -> Dict[str, Dict[str, Any]]:
        fields2type = {
            "name": str,
            "nb_rows": int,
        }

        query_result = self._psql_cmd(
            command=(
                'SELECT relname AS "name", n_live_tup AS "nb_rows" '
                "FROM pg_catalog.pg_stat_user_tables "
                "ORDER BY n_live_tup DESC"
            ),
            database=database_name,
            print_info=False,
        )

        lines = [line.split(",") for line in query_result.splitlines()]
        header = lines[0]
        info_dicts = [
            {f: fields2type.get(f)(v) for f, v in zip(header, line)} for line in lines[1:]
        ]
        info_tables = {d["name"]: d for d in info_dicts}

        return info_tables

    def table_length(
        self,
        database_name: str,
        table_name: str,
    ) -> int:
        result_query = self._postgresql_list(
            command=f"SELECT COUNT(*) FROM {table_name}",
            database=database_name,
        )
        count = int(result_query[0])
        return count

    def _psql_cmd(
        self,
        command: str,
        database: str = _DEFAULT_DATABASE,
        print_info: bool = True,
    ) -> str:
        host = "127.0.0.1"
        port = 5432

        shell_command = [
            f"{self._psql_bin}",
            f"{database}",
            f"--host={host}",
            f"--port={port}",
            "--csv",
            "-c",
        ] + [command]
        env = {
            "LD_LIBRARY_PATH": f"{self._libpq}",
        }
        out = self.platform.comm.shell(
            command=shell_command,
            current_dir=self._build_dir,
            environment=env,
            print_input=print_info,
            print_output=print_info,
            print_curdir=print_info,
        )

        return out

    def _postgresql_list(
        self,
        command: str,
        database: str = _DEFAULT_DATABASE,
    ) -> List[str]:  # TODO pushup? part of it
        cmd_result = self._psql_cmd(command, database=database, print_info=False)
        result = cmd_result.splitlines()[1:]  # filter out title header line
        return result


class PostgreSQLServerInstance(DBMSInstance):
    """Instance of a PostgreSQL server."""

    def __init__(
        self,
        build_dir: PathType,
        instance_dirpath: PathType,
        platform: Platform,
        numa_cpu_range: Optional[str] = None,
        numa_node_range: Optional[str] = None,
    ):
        super().__init__()

        self._build_dir = build_dir

        self._postgres_process = None
        self._client = PostgreSQLClient(
            platform=platform,
            user=getpass.getuser(),
            build_dir=self._build_dir,
        )
        self._data_dir = pathlib.Path(instance_dirpath)

        self.platform = platform

        self._numa_cpu_range = numa_cpu_range  # TODO moveup? or component-based approach
        self._numa_node_range = numa_node_range

        if not self.platform.comm.isdir(self._data_dir):
            # the instance points to a new database, we must initialize it
            self.platform.comm.makedirs(self._data_dir, exist_ok=False)
            self._init()
            self._configure()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def storage_dir(self) -> pathlib.Path:
        return self._data_dir

    @property
    def client(self) -> PostgreSQLClient:
        """
        Return a client connected to the postgreSQL server instance.

        Returns:
            PostgreSQLClient: a client connected to the postgreSQL server instance.
        """
        return self._client

    @property
    def pid(self) -> int:
        """Get the PID of the server instance.

        Raises:
            ValueError: if an inconsistency between postgres and the system is detected.

        Returns:
            int: the PID of the server instance.
        """
        subprocess_pid = self._postgres_process.pid

        postmaster_pid_filename = self._data_dir / "postmaster.pid"
        postmaster_pid = int(
            self.platform.comm.read_file(path=postmaster_pid_filename).splitlines()[0].strip()
        )

        if self.platform.comm.is_local:
            if subprocess_pid != postmaster_pid:
                raise ValueError(
                    f"Inconsistent pid (from {postmaster_pid_filename} and subprocessed pid."
                )

        return postmaster_pid

    def open(
        self,
        numa_cpu_range: Optional[str] = None,
        numa_node_range: Optional[str] = None,
    ) -> None:
        """
        Invoke the Postgres server
        """
        numa_cpu_range = numa_cpu_range if numa_cpu_range is not None else self._numa_cpu_range
        numa_node_range = numa_node_range if numa_node_range is not None else self._numa_node_range

        numactl = numactl_cmd_prefix(
            nb_numa_nodes=self.platform.nb_numa_nodes(),
            numa_cpu_range=numa_cpu_range,
            numa_node_range=numa_node_range,
        )
        postgres_bin = self._build_dir / "tmp_install/usr/local/pgsql/bin/postgres"

        postgres_cmd = numactl + [
            f"{postgres_bin}",
            "-D",
            f"{self._data_dir}",
        ]

        self._postgres_process = shell_async(
            platform=self.platform,
            command=postgres_cmd,
            stdout_path="/tmp/postgres.out",  # TODO check better options
            stderr_path="/tmp/postgres.err",  # TODO check better options
            current_dir=self._build_dir,
            environment=None,  # TODO?
            print_shell_cmd=True,
        )

        sleep_time = 1
        status = "?"
        # Try to ping mysql-server while it does not response and the process exist
        while not self._client.ping() and status != "":
            # TODO we only check the status of the local handle subprocess for now
            # (need status check to be implemented in remote comm layer to make it work better):
            status = self.platform.comm.get_process_status(
                process_handle=self._postgres_process._process  # pylint: disable=protected-access
            )
            time.sleep(sleep_time)
            sleep_time += 1
        self._client.ping_no_fail()

    def close(
        self,
        cleanup: bool = False,
    ) -> None:
        """
        Close the server instances.

        Args:
            cleanup (bool, optional):
                whether to clean up the data directory (the database information stored on disk).
                Defaults to False.
        """
        if self._client.ping():
            self._postgres_process.send_signal(signal_code=signal.SIGTERM, pid=self.pid)
        if self._postgres_process is not None:
            self._postgres_process.wait()
        if cleanup:
            assert len(str(self._data_dir).strip()) > 4
            shutil.rmtree(self._data_dir)

    def _init(self) -> None:
        """
        Close the current server instance if any is running (maybe a leftover from a previous
        execution).
        """
        self.close()

        init_bin = self._build_dir / "tmp_install/usr/local/pgsql/bin/initdb"
        libpq = self._build_dir / "src/interfaces/libpq"

        # Initialise the database by filling the data directory
        command = [
            f"{init_bin}",
            "-D",
            f"{self._data_dir}",
        ]
        env = {
            "LD_LIBRARY_PATH": f"{libpq}",
        }

        # TODO: use _numactl_cmd_prefix with range & node attributes
        numactl = []

        self.platform.comm.shell(
            command=numactl + command,
            current_dir=self._build_dir,
            environment=env,
            output_is_log=True,
        )

    def _configure(self) -> None:
        data_dir = self._data_dir

        def shell(cmd):
            self.platform.comm.shell(
                command=cmd,
                current_dir=data_dir,
                print_input=True,
                print_curdir=True,
                output_is_log=True,
            )

        pgconf_path = self._data_dir / "postgresql.conf"
        hbaconf_path = self._data_dir / "pg_hba.conf"

        # backup original config file and remove comments:
        shell(cmd=["sed", "-i.bak", "'/^[[:space:]]*#/d;/^$/d'", "postgresql.conf"])
        current_config = _config_str2dict(
            config_content=self.platform.comm.read_file(path=pgconf_path),
        )
        current_config["listen_addresses"] = "'0.0.0.0'"
        pgconfig_content = _config_dict2str(config_dict=current_config)
        self.platform.comm.write_content_to_file(
            content=pgconfig_content,
            output_filename=pgconf_path,
        )

        # backup original config file and remove comments:
        shell(cmd=["sed", "-i.bak", "'/^[[:space:]]*#/d;/^$/d'", "pg_hba.conf"])
        hba_content = self.platform.comm.read_file(path=hbaconf_path)
        listen_line = "host    all             all             0.0.0.0/0               trust"
        if listen_line not in hba_content:
            hba_content += listen_line
            self.platform.comm.write_content_to_file(
                content=hba_content,
                output_filename=hbaconf_path,
            )


class PostgreSQLServer(DBMS):
    """
    Object to build a PostgreSQL server and generate instances.
    This class is derived from DBMS. DBMS objects are usually attached
    to client SQL benchmarks (e.g. sysbench).
    See SQL helpers for more details.
    """

    def __init__(
        self,
        platform: Platform | None,
        src_dir_path: PathType,
        build_dir_path: PathType,
        instances_dir: PathType = "/tmp/benchkit_postgresqlserver",
    ):
        super().__init__(platform=platform)

        self._src_path = pathlib.Path(self.platform.comm.realpath(src_dir_path))
        self._build_dir = pathlib.Path(self.platform.comm.realpath(build_dir_path))
        self._data_dir = pathlib.Path(instances_dir)

    def dependencies(self) -> List[Dependency]:
        dependency_names = [
            "bison",
            "build-essential",
            "flex",
            "gdb",
            "git",
            "libreadline-dev",
            "zlib1g-dev",
        ]
        dependencies = [PackageDependency(name=n, platform=self.platform) for n in dependency_names]
        return super().dependencies() + dependencies

    def build_dir(
        self,
        **_kwargs,
    ) -> pathlib.Path:
        """
        Get the build directory of PostgreSQL server.

        Returns:
            pathlib.Path: the build directory of PostgreSQL server.
        """
        return self._build_dir

    def build(
        self,
        **_kwargs,
    ) -> None:
        if self._is_built():
            return

        build_dir = self._build_dir
        self.platform.comm.makedirs(path=build_dir, exist_ok=True)

        def build_cmd(command: Command) -> None:
            self.platform.comm.shell(
                command=command,
                current_dir=build_dir,
                output_is_log=True,
            )

        # Configure step:
        configure_script_path = self._src_path / "configure"
        if not configure_script_path.is_file():
            raise ValueError(f"configure script not found: {configure_script_path}")
        build_cmd([f"{configure_script_path}"])

        # Build the dbms:
        build_cmd(f"make -j {self.platform.nb_cpus()}")

        # Build other binaries:
        build_cmd(f"make -j {self.platform.nb_cpus()} world-bin")

        # Run tests:
        build_cmd(f"make -j {self.platform.nb_cpus()} check")

    def instance(
        self,
        build_dir: PathType,
        instance_dirname: PathType = "",
        data_cloned_from: PathType = "",
        numa_cpu_range: Optional[str] = None,
        numa_node_range: Optional[str] = None,
        additional_parameters: Optional[Dict[str, Any]] = None,
    ) -> PostgreSQLServerInstance:
        global_data_dir = pathlib.Path(self._data_dir)
        self.platform.comm.makedirs(global_data_dir, exist_ok=True)

        if instance_dirname:
            instance_path = global_data_dir / instance_dirname
        else:
            instance_path = tempfile.mkdtemp(prefix="instance-", dir=global_data_dir)
        if data_cloned_from:  # TODO comm layer in the body of this if
            src_instance_path = pathlib.Path(data_cloned_from)
            dst_instance_path = pathlib.Path(instance_path)
            src_data_path = src_instance_path / "data"
            dst_data_path = dst_instance_path / "data"

            assert os.path.isdir(src_data_path)
            assert not os.path.exists(dst_data_path)

            shutil.copytree(src=src_data_path, dst=dst_data_path)

        return PostgreSQLServerInstance(
            build_dir=build_dir,
            instance_dirpath=instance_path,
            platform=self.platform,
            numa_cpu_range=numa_cpu_range,
            numa_node_range=numa_node_range,
        )

    def clean(self) -> None:
        pass

    def clean_all(self) -> None:
        assert len(str(self._data_dir)) > 5
        shutil.rmtree(self._data_dir, ignore_errors=True)

    def sysbench_db_driver(self) -> str:
        return "pgsql"

    def _is_built(
        self,
    ) -> bool:
        force_rebuild = False

        if force_rebuild:
            return False

        postgres_executable = self._build_dir / "tmp_install/usr/local/pgsql/bin/postgres"
        result = self.platform.comm.isfile(postgres_executable)
        return result
