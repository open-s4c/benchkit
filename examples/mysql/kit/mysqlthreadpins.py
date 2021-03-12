#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Script to fetch the stack of mysqld process and find the required thread
to pin the log threads to specific cores.
"""

import re
import subprocess
import sys
from typing import Dict, Iterable, List

try:
    from benchkit.shell.shell import shell_out
except ModuleNotFoundError:

    def shell_out(
        cmd: str,
        print_input: bool = True,
        print_output: bool = True,
        **_kwargs,
    ) -> str:
        """
        Small version of shell_out if benchkit is not available in the current environment.
        Executes the given command.

        Args:
            cmd (str): command to execute.
            print_input (bool, optional): whether to print the command. Defaults to True.
            print_output (bool, optional): whether to print the output. Defaults to True.

        Returns:
            str: the output return by the executed command.
        """
        if print_input:
            print(f"[CMD] {cmd}")
        output = subprocess.check_output(
            cmd.split(),
            text=True,
        )
        if print_output:
            print(f"[OUT]\n{output}")
        return output


def get_tid(
    stack_keywords: Iterable[str],
    mysqld_pid: int,
) -> Dict[str, List[int]]:
    """
    Return the tid of the logging threads of the given mysqld process.

    Args:
        stack_keywords (Iterable[str]): keywords to find in function names of the stack of mysqld.
        mysqld_pid (int): PID of the mysqld process.

    Returns:
        Dict[str, List[int]]: the tid of the logging threads of the given mysqld process.
    """
    thread_ids = {stack_keyword: [] for stack_keyword in stack_keywords}
    stacks = get_daemon_stack(mysqld_pid=mysqld_pid)

    for tid, thread_stacks in stacks.items():
        for stack in thread_stacks:
            for stack_keyword in stack_keywords:
                if stack.find(stack_keyword) != -1:
                    thread_ids[stack_keyword].append(tid)
    return thread_ids


def get_daemon_stack(mysqld_pid: int) -> Dict[int, str]:
    """
    Attach to the given mysqld process with gdb and return its stack.

    Args:
        mysqld_pid (int): PID of the mysqld process to get the stack from.

    Returns:
        Dict[int, str]: return the stack of the given mysqld process.
    """
    thread_pattern = re.compile(r"\(LWP\s*(?P<tid>\d+)\)")

    gdb_cmd = [
        "sudo",
        "gdb",
        "-ex",
        "set confirm off",
        "-ex",
        f"attach {mysqld_pid}",
        "-ex",
        "thread apply all bt",
        "-ex",
        "quit",
    ]
    gdb_output = subprocess.check_output(gdb_cmd, text=True)
    gdb_lines = list(gdb_output.splitlines())
    start_line_idx = 0
    while not gdb_lines[start_line_idx].startswith("Thread "):
        start_line_idx += 1
    gdb_threadstack_lines = gdb_lines[start_line_idx:]

    stacks = {}
    current_thread = ""
    for line in gdb_threadstack_lines:
        match_result = thread_pattern.search(line)
        if match_result:
            tid = match_result.group("tid")
            stacks.setdefault(tid, [])
            current_thread = tid
        elif current_thread:
            stacks.get(current_thread).append(line)
    return stacks


def set_tid_affinity_by_pstack(
    mysqld_pid: int,
    log1_cpu_id: int,
    log2_cpu_id: int,
) -> None:
    """
    Set the affinity (thread to cpu assignment) by finding the TID on the process' stack.

    Args:
        mysqld_pid (int): PID of the mysqld process.
        log1_cpu_id (int): id of the CPU of the first logging thread.
        log2_cpu_id (int): id of the CPU of the second logging thread.
    """
    log_cpu_ids = [log1_cpu_id, log2_cpu_id]

    keywords = [
        "log_writer(log_t*)",
        "log_write_notifier(log_t*)",
        "log_flusher(log_t*)",
        "log_flush_notifier(log_t*)",
        "event_scheduler_thread ()",
        "srv_worker_thread()",
        "srv_purge_coordinator_thread()",
        "buf_dump_thread()",
        "fts_optimize_thread(ib_wqueue_t*)",
        "dict_stats_thread()",
        "srv_master_thread()",
        "buf_resize_thread()",
        "lock_wait_timeout_thread()",
        "log_checkpointer(log_t*)",
        "buf_flush_page_cleaner_thread()",
        "buf_flush_page_coordinator_thread(unsigned long)",
        "Clone_persist_gtid::periodic_write(",
    ]
    threads = get_tid(keywords, mysqld_pid)

    for i, key in enumerate(("log_flusher(log_t*)", "log_writer(log_t*)")):
        cmd = f"taskset -cp {log_cpu_ids[i]} {threads[key][0]}"
        shell_out(cmd)


def get_current_mysqld_pid() -> int:
    """
    Return the PID of the currently running mysqld process.

    Returns:
        int: the PID of the currently running mysqld process.
    """
    succeed = True
    try:
        out = shell_out("pgrep mysqld", print_input=False, print_output=False)
    except subprocess.CalledProcessError:
        succeed = False
    if not succeed:
        print("No mysqld process found.", file=sys.stderr)
        raise SystemExit(2)

    result = int(out.strip())
    return result


def main():
    """Main function of the script."""

    if len(sys.argv) < 3:
        print(
            (
                f"Usage: python3 {sys.argv[0]} core1 core2\n"
                f"Need to provide core identifiers for both log threads."
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)

    current_pid = get_current_mysqld_pid()
    log_core1, log_core2 = [int(sys.argv[i].strip()) for i in range(1, 3)]

    set_tid_affinity_by_pstack(
        mysqld_pid=current_pid,
        log1_cpu_id=log_core1,
        log2_cpu_id=log_core2,
    )


if __name__ == "__main__":
    main()
