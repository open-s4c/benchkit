# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for MySQL benchmark.
"""

import os
import os.path
import pathlib
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, Iterable, List, Optional

import mysqlconfigs
import mysqlthreadpins

from benchkit.commandwrappers.numactl import numactl_cmd_prefix
from benchkit.communication import LocalCommLayer
from benchkit.dependencies.dependency import Dependency
from benchkit.dependencies.packages import PackageDependency
from benchkit.helpers.sql import DBMS, DBMSInstance, SQLClient
from benchkit.platforms import Platform
from benchkit.shell.shellasync import shell_async
from benchkit.utils.types import PathType


class MySQLClient(SQLClient):
    """
    Benchmark object for the client in MySQL's benchmark.
    """

    def __init__(
        self,
        platform: Platform,
        user: str,
        build_dir: str,
    ):
        super().__init__(platform=platform)
        self._user = user
        self._build_dir = build_dir

    def ping(self) -> bool:
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
        self._mysqladmin_cmd("ping", print_info=False)

    def shutdown(self) -> None:
        self._mysqladmin_cmd("shutdown")

    def create_user(
        self,
        user: str,
        password: str,
    ) -> str:
        return self._mysql_cmd(f"CREATE USER '{user}' IDENTIFIED BY '{password}'")

    def grant_privileges(
        self,
        user: str,
    ) -> str:
        return self._mysql_cmd(f"GRANT ALL PRIVILEGES ON *.* TO {user}")

    def create_database(
        self,
        name: str,
    ) -> str:
        return self._mysql_cmd(f"CREATE DATABASE {name}")

    def list_databases(self) -> List[str]:
        databases = self._mysql_list("SHOW DATABASES")
        return databases

    def list_users(self) -> List[str]:
        users = self._mysql_list("SELECT User FROM mysql.user")
        return users

    def list_tables(
        self,
        database_name: str,
    ) -> List[str]:
        tables = self._mysql_list(f"SHOW TABLES FROM {database_name}")
        return tables

    def list_tables_info(
        self,
        database_name: str,
        fields: Iterable[str],
    ) -> Dict[str, Dict[str, Any]]:
        fields2mysql = {
            "name": "TABLE_NAME",
            "nb_rows": "TABLE_ROWS",
        }
        fields2type = {
            "name": str,
            "nb_rows": int,
        }

        select_fields = (
            ", ".join(f"{fields2mysql.get(f)} as '{f}'" for f in ["name"] + list(fields)) + " "
        )

        query_result = self._mysql_cmd(
            command=(
                f"SELECT {select_fields}"
                f"FROM INFORMATION_SCHEMA.TABLES "
                f"WHERE TABLE_SCHEMA = '{database_name}'"
            ),
            batch=True,
            print_info=False,
        )

        lines = [line.split("\t") for line in query_result.splitlines()]
        header = lines[0]
        info_dicts = [
            dict(
                map(  # t[0] = field name, t[1] = field value
                    lambda t: (t[0], fields2type.get(t[0])(t[1])),
                    zip(header, line),
                )
            )
            for line in lines[1:]
        ]
        info_tables = {d["name"]: d for d in info_dicts}

        return info_tables

    def table_length(
        self,
        database_name: str,
        table_name: str,
    ) -> int:
        result_query = self._mysql_list(f"SELECT COUNT(*) FROM {database_name}.{table_name}")
        count = int(result_query[0])
        return count

    def _bin_out(
        self,
        executable: str,
        command: List[str],
        print_info: bool = True,
    ) -> str:
        shell_command = [
            f"./bin/{executable}",
            "--user",
            self._user,
        ] + command
        out = self.platform.comm.shell(
            command=shell_command,
            current_dir=self._build_dir,
            print_input=print_info,
            print_output=print_info,
            print_curdir=print_info,
        )
        return out

    def _mysqladmin_cmd(
        self,
        command: str,
        print_info=True,
    ) -> str:
        return self._bin_out(executable="mysqladmin", command=[command], print_info=print_info)

    def _mysql_cmd(
        self,
        command: str,
        batch=False,
        print_info=True,
    ) -> str:
        batch_suffix = ["--batch"] if batch else []
        command_list = batch_suffix + ["-e", command]
        return self._bin_out(executable="mysql", command=command_list, print_info=print_info)

    def _mysql_list(
        self,
        command: str,
    ) -> List[str]:
        cmd_result = self._mysql_cmd(command, batch=True, print_info=False)
        result = cmd_result.splitlines()[1:]  # filter out title header line
        return result


class MySQLServerInstance(DBMSInstance):
    """Instance of the MySQL server."""

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

        self._mysqld_process = None
        self._client = MySQLClient(
            platform=platform,
            user="root",
            build_dir=self._build_dir,
        )
        self._instance_dir = pathlib.Path(instance_dirpath)
        self._config_path = self._instance_dir / "mysqld-config.cnf"
        self._data_dir = self._instance_dir / "data"

        self.platform = platform

        self._numa_cpu_range = numa_cpu_range
        self._numa_node_range = numa_node_range

        self._actual_nb_threads = None

        self.platform.comm.makedirs(self._instance_dir, exist_ok=True)

        if not self.platform.comm.isfile(self._config_path):
            # no configuration file detected
            config_dict = {
                "mysql": {
                    "default-character-set": "utf8",
                },
                "mysqld": {
                    "datadir": self._data_dir,
                    # avoids RSA issues with client/server connection:
                    "default_authentication_plugin": "mysql_native_password",
                    "innodb_log_file_size": "5M",
                },
            }

            mysqlconfigs.update_config_largerserver2(input_dict=config_dict)

            # TODO to remove; replace by "config_dict override parameter"
            if platform.hostname in ["core", "vm", "hlab"]:
                config_dict["mysqld"]["innodb_log_file_size"] = "5M"
                config_dict["mysqld"]["innodb_buffer_pool_size"] = "1G"

            config_str = self._config_to_ini(config_dict)
            self.platform.comm.write_content_to_file(
                content=config_str,
                output_filename=self._config_path,
            )

        if not self.platform.comm.isdir(self._data_dir):
            # the instance points to a new database, we must initialize it
            self.platform.comm.makedirs(self._data_dir, exist_ok=False)
            self._init()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def storage_dir(self) -> pathlib.Path:
        return self._instance_dir

    @property
    def client(self) -> MySQLClient:
        """
        Return the SQL client associated with the current server instance.

        Returns:
            MySQLClient: the SQL client associated with the current server instance.
        """
        return self._client

    @property
    def pid(self) -> int:
        """
        Return the pid of the mysqld process (the server).

        Returns:
            int: the pid of the mysqld process (the server).
        """
        return self._mysqld_process.pid

    @staticmethod
    def _config_to_ini(
        config: Dict[str, Dict[str, str]],
    ) -> str:
        def config_dict_to_paragraph(title: str, content: Dict[str, str]) -> str:
            str_content = "\n".join(
                [f"{k}={content[k]}" if content[k] is not None else f"{k}" for k in content]
            )
            result = f"[{title}]\n{str_content}\n"
            return result

        file_content = "\n".join(
            [config_dict_to_paragraph(title=key, content=config[key]) for key in config]
        )
        return file_content

    def open(
        self,
        numa_cpu_range: Optional[str] = None,
        numa_node_range: Optional[str] = None,
    ) -> None:
        """
        Invoke the MySQL daemon
        """
        numa_cpu_range = numa_cpu_range if numa_cpu_range is not None else self._numa_cpu_range
        numa_node_range = numa_node_range if numa_node_range is not None else self._numa_node_range

        numactl = numactl_cmd_prefix(
            nb_numa_nodes=self.platform.nb_numa_nodes(),
            numa_cpu_range=numa_cpu_range,
            numa_node_range=numa_node_range,
        )

        # We do not use `mysqld_safe` as it is adding a layer in the process tree
        mysqld_bin_path = "./bin/mysqld"

        verbose_log = True
        if verbose_log:
            self.platform.comm.shell(
                command=[mysqld_bin_path, "--version"],
                current_dir=self._build_dir,
                output_is_log=True,
            )
            self.platform.comm.shell(
                command=f"cat {self._config_path}",
                current_dir=self._build_dir,
                output_is_log=True,
            )

        mysqld_cmd = numactl + [
            mysqld_bin_path,
            f"--defaults-file={self._config_path}",
        ]

        self._mysqld_process = shell_async(
            platform=self.platform,
            command=mysqld_cmd,
            stdout_path="/tmp/mysql.out",
            stderr_path="/tmp/mysql.err",
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
            comm = LocalCommLayer()
            # pylint: disable=protected-access
            status = comm.get_process_status(process_handle=self._mysqld_process._process)
            time.sleep(sleep_time)
            sleep_time += 1
        self._client.ping_no_fail()

        # TODO fix, broken on remote version for now
        if self.platform.comm.is_local:
            # pylint: disable=protected-access
            self._actual_nb_threads = self.platform.comm.get_process_nb_threads(
                process_handle=self._mysqld_process._process
            )

    def close(
        self,
        cleanup: bool = False,
    ) -> None:
        """
        Close the current instance of MySQL server.

        Args:
            cleanup (bool, optional):
                whether to cleanup the underlying database (remove everything).
                Defaults to False.
        """
        if self._client.ping():
            self._client.shutdown()
        if self._mysqld_process is not None:
            self._mysqld_process.wait()
        if cleanup:
            assert len(str(self._data_dir).strip()) > 4
            shutil.rmtree(self._data_dir)

    def pin_threads(
        self,
        logging_cpu_1: int,
        logging_cpu_2: int,
    ) -> None:
        """
        Pin the logging threads to the given CPUs.

        Args:
            logging_cpu_1 (int): CPU id of the first logging thread.
            logging_cpu_2 (int): CPU id of the second logging thread.
        """
        mysqlthreadpins.set_tid_affinity_by_pstack(
            mysqld_pid=self.pid,
            log1_cpu_id=logging_cpu_1,
            log2_cpu_id=logging_cpu_2,
        )

    def _init(self) -> None:
        # Close the current server instance if any (maybe a leftover from a previous execution)
        self.close()

        # Initialise the database by filling the data directory
        command = [
            "./bin/mysqld",
            f"--defaults-file={self._config_path}",
            "--initialize-insecure",
        ]
        numactl = numactl_cmd_prefix(
            nb_numa_nodes=self.platform.nb_numa_nodes(),
            numa_cpu_range=self._numa_cpu_range,
            numa_node_range=self._numa_node_range,
        )
        self.platform.comm.shell(
            command=numactl + command,
            current_dir=self._build_dir,
            output_is_log=True,
        )


class MySQLServer(DBMS):
    """
    Instance of the MySQL server.
    """

    def __init__(
        self,
        platform: Platform | None,
        src_dir_path: PathType,
        build_dir_path: PathType,
        instances_dir: PathType = "/tmp/benchkit_mysqlserver",
    ):
        super().__init__(platform=platform)

        self._src_path = pathlib.Path(self.platform.comm.realpath(src_dir_path))
        self._build_dir = pathlib.Path(self.platform.comm.realpath(build_dir_path))
        self._data_dir = pathlib.Path(instances_dir)

        self._executables = [
            "mysqld",
            "mysql",
            "mysqladmin",
        ]

    def dependencies(self) -> List[Dependency]:
        os_release_file_content = self.platform.comm.read_file(path="/etc/os-release")
        os_attr = {}
        for line in os_release_file_content.splitlines():
            stripped_line = line.strip()
            if stripped_line:
                key, value = stripped_line.split("=")
                os_attr[key.strip()] = value.strip().replace('"', "")
        ubuntu1804 = os_attr.get("VERSION_ID") == "18.04"

        return super().dependencies() + [  # TODO commlayer
            PackageDependency("bison"),
            PackageDependency("build-essential"),
            PackageDependency("cmake"),
            PackageDependency("git"),
            PackageDependency("libldap2-dev"),
            PackageDependency("libncurses5-dev" if ubuntu1804 else "libncurses-dev"),
            PackageDependency("libsasl2-dev"),
            PackageDependency("libssl-dev"),
            PackageDependency("libudev-dev"),
            PackageDependency("pkg-config"),
            PackageDependency("perl"),
        ]

    def build_dir(
        self,
        mysql_mutex_type: str,
        lock: str,
        **kwargs,
    ) -> pathlib.Path:
        """
        Return the path to the build directory according to the provided build options.

        Args:
            mysql_mutex_type (str): type of MySQL mutex.
            lock (str): lock implementation of the mutex.

        Returns:
            pathlib.Path: the path to the build directory.
        """
        lock_use_bigsmall: bool = kwargs.get("lock_use_bigsmall")
        suffix = "-bs" if lock_use_bigsmall else ""
        if not lock:
            lock = "baseline"
        dirname = f"{mysql_mutex_type}-{lock}{suffix}"
        result = self._build_dir / dirname
        return result

    def build(
        self,
        lock_filename: str = "baseline",
        mysql_mutex_type: str = "event",
        lock_use_bigsmall: bool = False,
        lxe: bool = False,
        **kwargs,
    ) -> None:
        if not lock_filename:  # TODO better handling of locks
            lock_filename = "baseline"
        lock: str = kwargs.get("lock")

        # Possible values for mutex_type: event,sys,futex. default is "event":
        mysql_mutex_type_opt = mysql_mutex_type

        # Build conditionally if the important binaries are not there (unless rebuild is forced)
        if not self._is_built(mysql_mutex_type, lock_filename, lock_use_bigsmall):
            build_dir = self.build_dir(
                mysql_mutex_type=mysql_mutex_type,
                lock_filename=lock_filename,
                lock_use_bigsmall=lock_use_bigsmall,
                lock=lock,
            )
            boost_dir = self._build_dir / "libboost"

            self.platform.comm.makedirs(path=build_dir, exist_ok=True)

            def onoff(condition: bool):
                return "ON" if condition else "OFF"

            hisilicon_arch_specific_flags = (
                [
                    "-DCMAKE_C_FLAGS_RELWITHDEBINFO=-O3  -march=armv8-a+crypto+lse+crc -DNDEBUG",
                    "-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O3  -march=armv8-a+crypto+lse+crc -DNDEBUG",
                    "-DCMAKE_C_FLAGS=-O3  -march=armv8-a+crypto+lse+crc -DNDEBUG",
                    "-DCMAKE_CXX_FLAGS=-O3  -march=armv8-a+crypto+lse+crc -DNDEBUG",
                ]
                if "aarch64" == self.platform.architecture
                else []
            )
            cmake_cmd_hisilicon = (
                [
                    "cmake",
                    "-DCMAKE_EXPORT_COMPILE_COMMANDS=1",
                    "-DCMAKE_BUILD_TYPE=Release",
                    f"-DWLOCK={lock_filename.upper()}",
                    f"-DLOCK_BIGSMALL={onoff(lock_use_bigsmall)}",
                    f"-DVSYNC_LXE={onoff(lxe)}",
                    f"-DMUTEXTYPE={mysql_mutex_type_opt}",
                    "-DDOWNLOAD_BOOST=1",
                    f"-DWITH_BOOST={boost_dir}",
                ]
                + hisilicon_arch_specific_flags
                + [
                    "-DWITH_BLACKHOLE_STORAGE_ENGINE=0",
                    "-DWITH_FEDERATED_STORAGE_ENGINE=0",
                    "-DWITH_ARCHIVE_STORAGE_ENGINE=0",
                    "-DWITH_MYSQLX=OFF",
                    "-DFORCE_INSOURCE_BUILD=1",
                    # f'-DWITH_NUMA=1',# TODO TO CHECK
                    f"{self._src_path}",
                ]
            )

            cmake_cmd = cmake_cmd_hisilicon

            self.platform.comm.shell(
                command=cmake_cmd,
                current_dir=build_dir,
                output_is_log=True,
            )
            self.platform.comm.shell(
                command=f"make -j {self.platform.nb_cpus()}",
                current_dir=build_dir,
                output_is_log=True,
            )

    def instance(
        self,
        build_dir: PathType,
        instance_dirname: PathType = "",
        data_cloned_from: PathType = "",
        numa_cpu_range: Optional[str] = None,
        numa_node_range: Optional[str] = None,
        additional_parameters: Optional[Dict[str, Any]] = None,
    ) -> MySQLServerInstance:
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

        return MySQLServerInstance(
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
        return "mysql"

    def _is_built(
        self,
        mysql_mutex_type: str,
        lock: str,
        lock_use_bigsmall: bool,
    ) -> bool:
        force_rebuild = True
        if not lock:
            lock = "baseline"

        if force_rebuild:
            return False

        bin_dir = (
            self.build_dir(
                mysql_mutex_type=mysql_mutex_type,
                lock=lock,
                lock_use_bigsmall=lock_use_bigsmall,
            )
            / "bin"
        )

        paths_executables = [bin_dir / e for e in self._executables]
        result = all(self.platform.comm.isfile(p) for p in paths_executables)
        return result
