# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Helpers for SQL functions, like create database, executing queries, managing DBMS, etc.
"""

from typing import Any, Dict, Iterable, List, Optional

from benchkit.dependencies.dependency import Dependency
from benchkit.platforms import Platform, get_current_platform
from benchkit.utils.types import PathType


class SQLClient:
    """
    Represent a SQL client that connect to a DBMS server.
    The implementation depends on the DBMS and the DBMS is usually capable of producing a compatible
    SQLClient instance.
    """

    def __init__(self, platform: Platform):
        self.platform = platform

    def ping(self) -> bool:
        """
        Try to ping the server and return the result.

        Returns:
            bool: whether the ping succeeded.
        """
        raise NotImplementedError

    def ping_no_fail(self) -> None:
        """
        Ping the server, but does not allow the ping to fail.
        Raises an exception if it is the case.
        """
        raise NotImplementedError

    def shutdown(self) -> None:
        """Initiates a shutdown of the DBMS from the client."""
        raise NotImplementedError

    def create_user(
        self,
        user: str,
        password: str,
    ) -> str:
        """
        Create a user in the database.

        Args:
            user (str): name of the user to create.
            password (str): password of the user to create.

        Returns:
            str: _description_ TODO
        """
        raise NotImplementedError

    def grant_privileges(
        self,
        user: str,
    ) -> None:
        """
        Enable basic privileges to given user (create databases, create tables, etc.)

        Args:
            user (str): the name of the user to whom give the privileges.
        """
        raise NotImplementedError

    def create_database(
        self,
        name: str,
    ) -> str:
        """
        Create a database on the server.

        Args:
            name (str): name of the database to create.

        Returns:
            str: _description_ TODO
        """
        raise NotImplementedError

    def list_databases(self) -> List[str]:
        """
        Get the list of all databases on the connected DBMS.

        Returns:
            List[str]: the list of all databases on the connected DBMS.
        """
        raise NotImplementedError

    def list_users(self) -> List[str]:
        """
        Get the list of all users on the connected DBMS.

        Returns:
            List[str]: the list of all users on the connected DBMS.
        """
        raise NotImplementedError

    def list_tables(
        self,
        database_name: str,
    ) -> List[str]:
        """
        Get the list of all the tables of the provided database.

        Args:
            database_name (str): name of the database for which to list all tables.

        Returns:
            List[str]: the list of all the tables of the provided database.
        """
        raise NotImplementedError

    def list_tables_info(
        self,
        database_name: str,
        fields: Iterable[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get the list of tables of the provided database enriched with requested table-specific
        information.

        Args:
            database_name (str):
                name of the database to which to list all tables.
            fields (Iterable[str]):
                fields requested for each tables.

        Returns:
            Dict[str, Dict[str, Any]]:
                dictionary of all the tables. The keys in the main dict are the table names and the
                values are other dicts that map requested fields to values of these fields.
        """
        raise NotImplementedError

    def table_length(
        self,
        database_name: str,
        table_name: str,
    ) -> int:
        """
        Get the length of the provided table in the provided database.

        Args:
            database_name (str): name of the database to query.
            table_name (str): name of the table to query.

        Returns:
            int: the length of the provided table in the provided database.
        """
        raise NotImplementedError


class DBMSInstance:
    """
    Represent a running instance of a DBMS. Not to be confused with a DBMS, which represent the
    static information of the DBMS.
    """

    def __init__(self):
        pass

    @property
    def storage_dir(self) -> str:
        """
        Get the path where the DBMS store the databases.

        Returns:
            str: the path where the DBMS store the databases.
        """
        raise NotImplementedError

    def open(
        self,
        numa_cpu_range: Optional[str] = None,
        numa_node_range: Optional[str] = None,
    ) -> None:
        """
        Open the DBMS instance.
        """
        raise NotImplementedError


class DBMS:
    """
    Represent the static information of a DataBase Management System (e.g. MySQL, postgresql, etc.).
    This is the entry point that generates the DBMSInstance and the SQLCLient.
    """

    def __init__(
        self,
        platform: Platform | None,
    ):
        self.platform = get_current_platform() if platform is None else platform

    def dependencies(self) -> List[Dependency]:
        """
        Get the dependencies of the DBMS.

        Returns:
            List[Dependency]: the list of dependencies of the DBMS.
        """
        return []

    def prebuild_bench(self, **_kwargs) -> None:
        """
        Pre-build the DBMS. TODO change method name
        """

    def build(self, **_kwargs) -> None:
        """
        Build the DBMS.
        """
        raise NotImplementedError()

    def instance(
        self,
        build_dir: PathType,
        instance_dirname: PathType = "",
        data_cloned_from: PathType = "",
        numa_cpu_range: Optional[str] = None,
        numa_node_range: Optional[str] = None,
        additional_parameters: Optional[Dict[str, Any]] = None,
    ) -> DBMSInstance:
        """
        Create a DBMSInstance for the current DBMS.
        It assumes the DBMS is already built.

        Args:
            build_dir (PathType):
                path where to DBMS has been built.
            instance_dirname (PathType, optional):
                Name of the directory of this specific instance. Defaults to "".
            data_cloned_from (PathType, optional):
                Path to the data directory of another instance to clone from.
                If "", create a fresh data directory. Defaults to "".
            numa_cpu_range (Optional[str], optional):
                CPU range for the executable pre-pended with numactl. Defaults to None.
                TODO command wrapper
            numa_node_range (Optional[str], optional):
                Node range for the executable pre-prended with numactl. Defaults to None.
                TODO command wrapper
            additional_parameters (Optional[Dict[str, Any]], optional):
                Dict of other parameters that can be interpreted by the specific instances.
                Defaults to None.

        Returns:
            DBMSInstance:
                instance of the DBMS that allows to control the DBMS.
        """
        raise NotImplementedError

    def clean(self) -> None:
        """Clean the DBMS build."""

    def clean_all(self) -> None:
        """Clean all databases TODO check"""

    def sysbench_db_driver(self) -> str:
        """
        Return the db_driver name of this DBMS for sysbench.
        This is a parameter sysbench must give on its own command line to configure the client
        connecting to the DBMS server.

        Returns:
            str: the db_driver name of this DBMS for sysbench.
        """
        raise NotImplementedError()
