# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `taskset` utility which allows to control on what CPU or set of CPUs the
threads of the wrapped command are scheduled.
"""

from typing import List, Optional

from benchkit.platforms import Platform, get_current_platform
from benchkit.utils.types import CpuOrder

from . import CommandWrapper, PackageDependency


class TasksetWrap(CommandWrapper):
    """Command wrapper for the `taskset` utility."""

    def __init__(
            self,
            platform: Platform | None = None,
            set_all_cpus: bool = False,
        ):
        super().__init__()
        self.platform = platform if platform is not None else get_current_platform()
        self.set_all_cpus = set_all_cpus

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("util-linux"),  # taskset executable
        ]

    def command_prefix(
        self,
        cpu_order: CpuOrder = None,
        master_thread_core: Optional[int] = None,
        nb_threads: Optional[int] = None,
        **kwargs,
    ) -> List[str]:
        cmd_prefix = super().command_prefix(
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            **kwargs,
        )

        mtc = master_thread_core

        if self.set_all_cpus:
            if cpu_order is None or nb_threads is None:
                return []

            cpu_order_list = self.platform.cpu_order(provided_order=cpu_order)

            cpu_order_list = [str(x) for x in cpu_order_list[0:nb_threads]]
            cpu_order_str = ','.join(cpu_order_list)

            cmd_prefix = ["taskset", "--cpu-list", cpu_order_str] + cmd_prefix
        else:
            if mtc is None:
                if cpu_order is None:
                    return []

                cpu_order_list = self.platform.cpu_order(provided_order=cpu_order)

                mtc = self.platform.master_thread_core_id(
                    cpu_order_list=cpu_order_list,
                )

            cmd_prefix = ["taskset", "--cpu-list", str(mtc)] + cmd_prefix

        return cmd_prefix
