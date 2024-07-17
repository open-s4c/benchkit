#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for postgresql benchmark.
"""

import os
import os.path
import pathlib

from postgresql import PostgreSQLServer
from sysbench import sysbench_campaign

from benchkit.campaign import CampaignSuite
from benchkit.platforms import get_current_platform
from benchkit.utils.git import clone_repo

NB_RUNS = 1
DURATION_SECONDS = 10
WARMUP_SECONDS = 1

variables = [
    {
        # build variables:
        "lock": "baseline",
        "lock_filename": "baseline",
        # run variables:
        "lua_script_filenames": ["oltp_update_index.lua"],
        "nb_tables": 16,
        "table_size": 100,  # TODO: Increase size for final campaign
        "warmup_seconds": WARMUP_SECONDS,
        "dbms_numa_node_range": None,
        "dbms_numa_cpu_range": None,
        "dbms_logging_cores": None,
        "sysbench_threads": 3,
        "sb_numa_cpu_range": None,
        "cpu_order": None,
        "master_thread_core": None,
    }
]


def main() -> None:
    """Main function of the script."""
    platform = get_current_platform()

    work_dir = pathlib.Path(os.path.expanduser("~/workspace/"))
    sysbench_src_dir = work_dir / "sysbench"
    postgresql_src_dir = work_dir / "postgresql"
    postgres_build_dir = work_dir / "postgresql-server-build"

    os.makedirs(work_dir, exist_ok=True)
    clone_repo(
        repo_url="https://git.postgresql.org/git/postgresql.git",
        repo_src_dir=postgresql_src_dir,
        tag="REL_15_2",
    )
    clone_repo(
        repo_url="https://github.com/akopytov/sysbench.git",
        repo_src_dir=sysbench_src_dir,
        tag="1.0.20",
    )

    dbms = PostgreSQLServer(
        platform=platform,
        src_dir_path=postgresql_src_dir,
        build_dir_path=postgres_build_dir,
    )
    campaign = sysbench_campaign(
        name="postgres_sysbench",
        dbms=dbms,
        client_platform=None,
        db_host="127.0.0.1",
        db_port=5432,
        benchmark=None,
        sysbench_src_dir=sysbench_src_dir,
        freshdb_foreach_run=False,
        nb_runs=NB_RUNS,
        benchmark_duration_seconds=DURATION_SECONDS,
        bench_variables=variables,
        enable_data_dir=True,
        continuing=False,
    )

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
