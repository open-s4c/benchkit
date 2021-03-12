# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Examples of configurations for MySQL server.
"""

from typing import Dict


def update_config_cpubound(input_dict: Dict[str, Dict[str, str]]) -> None:
    """
    Update the given configuration dict to be a cpu bound database server.

    Args:
        input_dict (Dict[str, Dict[str, str]]): the updated configuration dict for MySQL server.
    """
    input_dict["mysqld"]["mysqlx"] = "0"
    input_dict["mysqld"]["log-error-verbosity"] = "3"
    input_dict["mysqld"]["server-id"] = "1"
    input_dict["mysqld"]["innodb_fast_shutdown"] = "0"
    input_dict["mysqld"]["binlog_format"] = "ROW"
    input_dict["mysqld"]["binlog_row_image"] = "MINIMAL"
    input_dict["mysqld"]["max_prepared_stmt_count"] = "1000000"
    input_dict["mysqld"]["max_connections"] = "4096"
    input_dict["mysqld"]["back_log"] = "6000"
    input_dict["mysqld"]["table_open_cache"] = "100000"
    input_dict["mysqld"]["table_open_cache_instances"] = "64"
    input_dict["mysqld"]["innodb_open_files"] = "4000"
    input_dict["mysqld"]["innodb_buffer_pool_size"] = "10G"  # or "80G"
    input_dict["mysqld"]["innodb_buffer_pool_instances"] = "8"
    input_dict["mysqld"]["innodb_log_file_size"] = "1M"  # or "5G"
    input_dict["mysqld"]["innodb_log_files_in_group"] = "4"
    input_dict["mysqld"]["innodb_log_buffer_size"] = "64M"
    input_dict["mysqld"]["innodb_max_dirty_pages_pct"] = "90"
    input_dict["mysqld"]["innodb_max_dirty_pages_pct_lwm"] = "10"
    input_dict["mysqld"]["innodb_lru_scan_depth"] = "2048"
    input_dict["mysqld"]["innodb_flush_method"] = "O_DIRECT"
    input_dict["mysqld"]["innodb_flush_neighbors"] = "0"
    input_dict["mysqld"]["innodb_page_cleaners"] = "8"
    input_dict["mysqld"]["innodb_buffer_pool_dump_at_shutdown"] = "0"
    input_dict["mysqld"]["innodb_buffer_pool_load_at_startup"] = "0"
    input_dict["mysqld"]["innodb_io_capacity"] = "12000"
    input_dict["mysqld"]["innodb_io_capacity_max"] = "24000"
    input_dict["mysqld"]["innodb_read_io_threads"] = "16"
    input_dict["mysqld"]["innodb_write_io_threads"] = "16"
    input_dict["mysqld"]["innodb_purge_threads"] = "8"
    input_dict["mysqld"]["innodb_adaptive_hash_index"] = "0"
    input_dict["mysqld"]["join_buffer_size"] = "256K"
    input_dict["mysqld"]["sort_buffer_size"] = "256K"
    input_dict["mysqld"]["innodb_numa_interleave"] = "1"


def update_config_largerserver(input_dict: Dict[str, Dict[str, str]]) -> None:
    """
    Update the given configuration dict to be run efficiently on a large server with many CPUs and
    a large amount of memory.

    Args:
        input_dict (Dict[str, Dict[str, str]]): the updated configuration dict for MySQL server.
    """
    sql_mode = "STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION,NO_AUTO_VALUE_ON_ZERO,STRICT_ALL_TABLES"
    new_dict = {
        "autocommit": "1",
        "back_log": "256",
        "binlog_cache_size": "1M",
        "binlog_format": "ROW",
        "default_storage_engine": "InnoDB",
        "innodb_data_file_path": "ibdata1:1000M:autoextend",
        "innodb_log_buffer_size": "128M",
        "innodb_log_file_size": "4G",
        "innodb_log_files_in_group": "5",
        "read_only": "0",
        "slow_query_log": "1",
        "sync_binlog": "1",
        "transaction_isolation": "REPEATABLE-READ",  # REPEATABLE-READ READ-COMMITTED
        "innodb_file_per_table": "ON",
        "server_id": 1,
        "bind-address": "0.0.0.0",
        "character_set_server": "latin1",
        "expire_logs_days": "1",
        "innodb_flush_method": "O_DIRECT",
        "innodb_open_files": "1024",
        "key_buffer_size": "128M",
        "max_binlog_size": "67108864",
        "open_files_limit": "500000",
        "skip-ssl": None,
        "skip-external-locking": None,
        "skip-name-resolve": None,
        "skip-slave-start": None,
        "skip-symbolic-links": None,
        "slave_net_timeout": "60",
        "sort_buffer_size": "262144",
        "sql_mode": sql_mode,
        "thread_cache_size": "128",
        "innodb_lru_scan_depth": "4096",
        "innodb_buffer_pool_size": "250G",
        "max_connections": "10728",
        "innodb_flush_neighbors": "0",
        "innodb_io_capacity": "20000",
        "innodb_page_cleaners": "16",
        "innodb_buffer_pool_instances": "16",
        "innodb_write_io_threads": "32",
        "innodb_read_io_threads": "24",
        "innodb_max_dirty_pages_pct": "20",
        "innodb_purge_threads": "32",
        "innodb_flush_log_at_trx_commit": "1",
        "performance_schema": "OFF",
        "table_open_cache": "8000",
        "table_open_cache_instances": "24",
        "innodb_doublewrite": "0",
        "innodb_checksum_algorithm": "none",
        "binlog_checksum": "none",
        "innodb_log_checksums": "0",
        "innodb_spin_wait_delay": "12",
        "innodb_sync_spin_loops": "25",
        "innodb_adaptive_hash_index": "1",
        "innodb_adaptive_hash_index_parts": "48",
    }

    if "mysqld" not in input_dict:
        input_dict["mysqld"] = {}
    input_dict["mysqld"].update(new_dict)


def update_config_largerserver2(input_dict: Dict[str, Dict[str, str]]) -> None:
    """
    Update the given configuration dict to be run efficiently on a large server with many CPUs and
    a large amount of memory.

    Args:
        input_dict (Dict[str, Dict[str, str]]): the updated configuration dict for MySQL server.
    """
    new_dict = {
        "open_files_limit": "50000",
        "max_connections": "20000",
        "back_log": "800",  # Set the number of session request caches
        "max_prepared_stmt_count": "128000",
        "explicit_defaults_for_timestamp": "true",
        "performance_schema": "OFF",
        "skip_name_resolve": None,
        "skip_ssl": None,
        "skip-log-bin": None,
        "table_open_cache": "8000",
        "table_open_cache_instances": "16",
        "innodb_doublewrite": "0",
        # file
        "default_storage_engine": "InnoDB",
        "character_set_server": "utf8",
        "innodb_file_per_table": None,  # Set up one file per table
        "innodb_log_file_size": "128G",
        "innodb_log_files_in_group": "2",  # Set the number of logfile groups
        "innodb_open_files": "4000",  # Set the maximum number of open tables
        "innodb_max_undo_log_size": "4G",
        "innodb_data_file_path": "ibdata1:1G:autoextend",
        "innodb-undo-log-truncate": "OFF",
        # buffers
        "innodb_buffer_pool_size": "196G",  # Set buffer poll size, usually 60% of server memory
        "innodb_buffer_pool_instances": "64",  # Nb buffer pool instances to improve concurrency
        "innodb_log_buffer_size": "512M",
        # tune
        # Every time a transaction is committed, MySQL will write the log buffer data to the log
        # file and flush it to the disk:
        "innodb_flush_log_at_trx_commit": "1",
        "innodb_use_native_aio": "1",  # Enable asynchronous IO
        "innodb_spin_wait_delay": "60",  # Prevent entry into system spin
        "innodb_sync_spin_loops": "40",  # Number of spin_loops cycles to prevent system spin
        "innodb_flush_method": "O_DIRECT",  # Opening/flashing modes of innodb data files; redo logs
        "innodb_io_capacity": "20000",  # Maximum iops limit for innodb background thread per second
        # Maximum iops limit for innodb background threads per second under pressure:
        "innodb_io_capacity_max": "40000",
        # Set the number of dirty pages that the page cleaner thread cleans each time:
        "innodb_lru_scan_depth": "4000",
        "innodb_page_cleaners": "10",  # Set the number of threads to write dirty data to disk
        # perf special
        # Detect all pages in the extent where the page is located.
        # If it is a dirty page, refresh it together, and the SSD turns off this function:
        "innodb_flush_neighbors": "0",
        "innodb_write_io_threads": "4",  # Set the number of write threads G
        "innodb_read_io_threads": "20",  # Set the number of reading threads
        "innodb_purge_threads": "4",  # Number of threads to recycle used and allocated undo pages
        "innodb_max_dirty_pages_pct": "90",  # default->75
        "innodb_max_dirty_pages_pct_lwm": "10",  # default->0
        "innodb_adaptive_hash_index": "1",  # [=1:62w->63w]
        "innodb_adaptive_hash_index_parts": "64",
        "innodb_buffer_pool_dump_at_shutdown": "OFF",
        "innodb_buffer_pool_load_now": "OFF",
        "innodb_buffer_pool_dump_pct": "100",
        "innodb_buffer_pool_load_at_startup": "OFF",
        "thread_cache_size": "600",
        "innodb_change_buffer_max_size": "50",
        "innodb_sync_array_size": "1",
    }

    if "mysqld" not in input_dict:
        input_dict["mysqld"] = {}
    input_dict["mysqld"].update(new_dict)

    # 128G is more than the RAM (ramfs)
    input_dict["mysqld"]["innodb_log_file_size"] = "32G"  # can also be '16G'
    # 196G is too much for ramfs
    input_dict["mysqld"]["innodb_buffer_pool_size"] = "282G"  # can also be '1G'
    # O_DIRECT triggers bug with ramfs
    input_dict["mysqld"]["innodb_flush_method"] = "nosync"
