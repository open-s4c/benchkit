# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for the locktorture benchmark (kernel module).

Useful documentation about the benchmark:
https://www.kernel.org/doc/html/latest/locking/locktorture.html

Arguments of the single_run() method are documented in locktorture doc:
  https://www.kernel.org/doc/html/v5.10/locking/locktorture.html
and in locktorture source code:
  https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/kernel/locking/locktorture.c
"""

import os.path
import re
import time
from typing import Any, Dict, Iterable, List, Tuple

from benchkit.benchmark import (
    Benchmark,
    CommandAttachment,
    CommandWrapper,
    PostRunHook,
    PreRunHook,
    SharedLib,
)
from benchkit.dependencies.packages import KernelModuleDependency
from benchkit.platforms import Platform
from benchkit.platforms.register import get_registered_platform
from benchkit.utils import parselog, systemactions
from benchkit.utils.dir import get_curdir, parentdir
from benchkit.utils.types import CpuOrder


class LockTortureBench(Benchmark):
    """Benchmark object for locktorture benchmark."""

    def __init__(
        self,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        platform: Platform | None = None,
    ):
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            pre_run_hooks=pre_run_hooks,
            shared_libs=shared_libs,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform

        script_path = get_curdir(__file__)
        lt_git_path = parentdir(script_path)

        self._bench_src_path = os.path.realpath(lt_git_path)

    @property
    def bench_src_path(self):
        return self._bench_src_path

    @staticmethod
    def get_build_var_names():
        return []

    @staticmethod
    def get_run_var_names():
        return [
            "cpu_order",
            "nwriters_stress",
            "nreaders_stress",
            "torture_type",
            "stat_interval",
            "stutter",
            "shuffle_interval",
            "verbose",
        ]

    @staticmethod
    def get_tilt_var_names():
        return []

    @staticmethod
    def _parse_results(
        log_output: str,
        benchmark_duration_seconds: int,
        torture_type: str | None,
        stat_interval: int | None,
    ) -> Dict[str, Any]:
        if torture_type is None:
            torture_type = "spin_lock"  # default value
        if stat_interval is None:
            stat_interval = 60

        raw_output_lines = parselog.loglines_from_module(
            log_output=log_output,
            start=f"{torture_type}-torture:--- Start of test:",
            end=f"{torture_type}-torture:--- End of test: SUCCESS",
            module_name=None,
        )

        main_write_statistics = []
        trailing_write_statistics = []
        current_write_statistics = main_write_statistics
        last_total = 0
        parsed_args = {}
        for line in raw_output_lines:
            if "Start of test:" in line:
                raw_args_str = line.split("Start of test:")[-1].strip()
                parsed_args = {
                    f"inputs-parsed/{k}": int(v)
                    for k, v in [arg.split("=", 1) for arg in raw_args_str.split()]
                }

            if "Stopping lock_torture" in line:
                current_write_statistics = trailing_write_statistics

            m = re.match(
                pattern=(
                    r".*Writes:\s+"
                    r"Total:\s+(?P<total>\d+)\s+"
                    r"Max/Min:\s+(?P<max>\d+)/(?P<min>\d+)\s+.*"
                    r"Fail:\s+(?P<fails>\d+)"
                ),
                string=line,
            )
            if m is not None:
                write_stat_dict = {k: int(v) for k, v in m.groupdict().items()}
                total = write_stat_dict["total"]
                write_stat_dict["diff"] = total - last_total

                current_write_statistics.append(write_stat_dict)
                last_total = total

        if not main_write_statistics:
            raise ValueError("Unable to parse locktorture results.")

        # keep the last "nb_stats_to_keep" statistics:
        nb_stats_to_keep = benchmark_duration_seconds // stat_interval
        filtered_write_statistics = main_write_statistics[-nb_stats_to_keep:]

        diffs = [v["diff"] for v in filtered_write_statistics]
        sum_diffs = sum(diffs)

        all_write_statistics = main_write_statistics + trailing_write_statistics
        last_write_statistics = all_write_statistics[-1]

        nb_threads = parsed_args.get("inputs-parsed/nwriters_stress") + parsed_args.get(
            "inputs-parsed/nreaders_stress"
        )

        measurement_dict = {
            "nb_threads": nb_threads,
            "duration": benchmark_duration_seconds,
            "global_count": sum_diffs,
            "last_writes_total": last_write_statistics["total"],
            "last_writes_max": last_write_statistics["max"],
            "last_writes_min": last_write_statistics["min"],
            "last_writes_fails": last_write_statistics["fails"],
        }

        result_dict = parsed_args | measurement_dict

        return result_dict

    def dependencies(self):
        return super().dependencies() + [
            KernelModuleDependency("locktorture"),
        ]

    def build_tilt(self, **kwargs):
        raise NotImplementedError("Tilt is not necessary for this benchmark.")

    def prebuild_bench(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        **kwargs,
    ) -> None:
        # We assume the lock torture module is already built with the currently running kernel
        pass

    def build_bench(
        self,
        **kwargs,
    ):
        pass

    def clean_bench(self):
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        cpu_order: CpuOrder = None,
        nwriters_stress: int | None = None,
        nreaders_stress: int | None = None,
        torture_type: str | None = None,
        stat_interval: int | None = None,
        stutter: int | None = None,
        shuffle_interval: int | None = None,
        verbose: int | None = None,
        **_kwargs,
    ):
        torture_types = [
            "lock_busted",
            "spin_lock",
            "spin_lock_irq",
            "rw_lock",
            "rw_lock_irq",
            "mutex_lock",
            "rtmutex_lock",
            "rwsem_lock",
        ]
        if (torture_type is not None) and (torture_type not in torture_types):
            raise ValueError(f"Invalid torture type: {torture_type}")

        locktorture_options = []
        locktorture_options += (
            [f"nwriters_stress={nwriters_stress}"] if nwriters_stress is not None else []
        )
        locktorture_options += (
            [f"nreaders_stress={nreaders_stress}"] if nreaders_stress is not None else []
        )
        locktorture_options += [f"torture_type={torture_type}"] if torture_type is not None else []
        locktorture_options += (
            [f"stat_interval={stat_interval}"] if stat_interval is not None else []
        )
        locktorture_options += [f"stutter={stutter}"] if stutter is not None else []
        locktorture_options += (
            [f"shuffle_interval={shuffle_interval}"] if shuffle_interval is not None else []
        )
        locktorture_options += [f"verbose={verbose}"] if verbose is not None else []
        locktorture_command = ["sudo", "modprobe", "locktorture"] + locktorture_options

        # System operations to avoid noise
        systemactions.sync_filesystems(comm_layer=self.platform.comm)
        systemactions.drop_caches(comm_layer=self.platform.comm)
        time.sleep(1)

        warmup_seconds = 4 * stat_interval if stat_interval >= 3 else 5

        with systemactions.DmesgLog(comm_layer=self.platform.comm) as dmesg:
            self.platform.comm.shell(command=locktorture_command)
            time.sleep(1)
            self._pin_kthreads(cpu_order=cpu_order)

            time.sleep(warmup_seconds + benchmark_duration_seconds)
            self.platform.comm.shell(command="sudo rmmod locktorture")
            time.sleep(2)

        log_output = dmesg.log

        results = self._parse_results(
            log_output=log_output,
            benchmark_duration_seconds=benchmark_duration_seconds,
            torture_type=torture_type,
            stat_interval=stat_interval,
        )
        return results

    def _get_kthreads_locktorture(self) -> List[Tuple[int, str]]:
        def match_locktorture_thead(line: str) -> Tuple[int, str] | None:
            m = re.match(pattern=r"root\s+(\d+).*\[(lock_torture_.+)\]", string=line)
            if m is None:
                return None
            pid, name = m.groups()
            return int(pid), name

        ps_output = self.platform.comm.shell(command="ps -ef", shell=False)
        lt_threads = sorted(
            [
                ltt
                for ps_line in ps_output.splitlines()
                if (ltt := match_locktorture_thead(line=ps_line)) is not None
            ],
            key=lambda e: e[0],
        )
        return lt_threads

    def _taskset_thread(
        self,
        pid: int,
        cpu_list: Iterable[int],
    ) -> None:
        cpu_list_str = ",".join(map(str, cpu_list))
        command = f"sudo taskset -p --cpu-list {cpu_list_str} {pid}"
        self.platform.comm.shell(command=command)

    def _pin_kthreads(self, cpu_order: CpuOrder) -> None:
        if cpu_order is None:
            return

        # TODO refactor when pushing up
        target_hostname = self.platform.hostname
        platform = get_registered_platform(machine_name=target_hostname)
        cpu_list = platform.cpu_order(provided_order=cpu_order)

        lt_threads = self._get_kthreads_locktorture()

        for i, (pid, _) in enumerate(lt_threads, start=0):
            cpu = cpu_list[i % len(cpu_list)]  # round-robin assignment style
            self._taskset_thread(pid=pid, cpu_list=[cpu])
