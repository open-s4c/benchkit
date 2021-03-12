#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for MySQL benchmark.
"""

import os.path

from mysqlserver import MySQLServer
from sysbench import sysbench_campaign

from benchkit.campaign import CampaignSuite
from benchkit.helpers.linux.predictable.predlinux import PredLinux
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import get_curdir


def main():
    """Main function of the script."""
    long_run = True
    preddo = False
    nb_runs = 1
    lua_script_filename = "oltp_update_index.lua"

    platform = get_current_platform()
    hostname = platform.hostname

    if long_run and hostname.startswith("node"):
        duration = 60
        sysbench_threads = 300
        nb_tables = 100
        table_size = 1_000_000
        warmup_seconds = 10
        numa_node_range = "2-3" if platform.nb_numa_nodes() == 4 else None
        nb_cpus = platform.nb_cpus()
        if 128 == nb_cpus:
            numa_cpu_range = "66-127"
            logging_cores = (64, 65)
        elif 96 == nb_cpus:
            numa_cpu_range = "50-95"
            logging_cores = (48, 49)
        else:
            numa_cpu_range = None
            logging_cores = None
    else:
        duration = 5
        sysbench_threads = 3
        nb_tables = 16
        table_size = 100
        warmup_seconds = 0
        numa_cpu_range = None
        numa_node_range = None
        logging_cores = None

    variables = [
        {
            # build variables:
            "lock": "baseline",
            "lock_filename": "baseline",
            "mysql_mutex_type": "event",
            # run variables:
            "numa_cpu_range": numa_cpu_range,
            "numa_node_range": numa_node_range,
            "sysbench_threads": sysbench_threads,
            "logging_cores": logging_cores,
            "cpu_order": None,  # TODO?
            "use_lse": False,
            "atomics": None,
            "benchmark_duration_seconds": duration,
            "master_thread_core": None,
            "lua_script_filename": lua_script_filename,
            "nb_tables": nb_tables,
            "table_size": table_size,
            "warmup_seconds": warmup_seconds,
        }
    ]

    deps_dir = get_curdir(__file__) / "deps"
    sysbench_src_dir = (deps_dir / "sysbench").resolve()
    mysql_src_dir = (deps_dir / "mysql-server").resolve()
    mysql_build_dir = os.path.expanduser("~/workspace/mysql-server-build")

    dbms = MySQLServer(
        platform=platform,
        src_dir_path=mysql_src_dir,
        build_dir_path=mysql_build_dir,
    )

    campaign = sysbench_campaign(
        name="mysql_sysbench",
        dbms=dbms,
        client_platform=platform,
        sysbench_src_dir=sysbench_src_dir,
        freshdb_foreach_run=False,
        nb_runs=nb_runs,
        benchmark_duration_seconds=duration,
        bench_variables=variables,
        enable_data_dir=True,
        continuing=False,
    )

    campaigns = [campaign]

    if preddo:
        predlinux = PredLinux()
        predlinux.preddo(
            frequency_to_set=2600,
            expected_nb_isolated_cpus=0,
        )

    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
