# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `numactl` utility which allows to control on what NUMA node the threads of
the wrapped command are assigned and on what NUMA node the memory is allocated (or select a specific
allocation policy).
"""

from typing import Iterable, List

from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import get_current_platform


class NumactlWrap(CommandWrapper):
    """Command wrapper for the `numactl` utility."""

    def __init__(
        self,
        membind: bool,
        local_alloc: bool,
        interleave_nodes: Iterable[int] | None,
    ) -> None:
        super().__init__()

        self._membind = membind
        self._local_alloc = local_alloc
        self._interleave_nodes = list(interleave_nodes) if interleave_nodes is not None else None

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("numactl"),
        ]

    def command_prefix(
        self,
        **kwargs,
    ) -> List[str]:
        cmd_prefix = super().command_prefix(**kwargs)

        options = []
        if self._membind:
            nodes = []

            mtc = kwargs["master_thread_core"] if "master_thread_core" in kwargs else None
            platform = kwargs["platform"] if "platform" in kwargs else get_current_platform()
            if mtc is not None:
                # node id of the mtc:
                node_mtc = mtc // (platform.nb_cpus() // platform.nb_numa_nodes())
                nodes = [node_mtc]

            if nodes:
                nodes_str = ",".join(map(str, nodes))
                options.append(f"--membind={nodes_str}")
        if self._local_alloc:
            options.append("--localalloc")
        if self._interleave_nodes is not None:
            options.append(f"--interleave={','.join(map(str, self._interleave_nodes))}")

        numactl_prefix = ["numactl"] + options

        cmd_prefix = numactl_prefix + cmd_prefix
        return cmd_prefix


def numactl_cmd_prefix(
    nb_numa_nodes: int,
    numa_cpu_range: str | None = None,
    numa_node_range: str | None = None,
) -> List[str]:
    """
    Helper for some benchmark, to define the command prefix according to nodes or cpu ranges.
    """

    # TODO warning, this does not support cpuisol
    numactl = []
    if numa_cpu_range is not None:
        numactl += ["-C", str(numa_cpu_range)]
    if numa_node_range is not None:
        include_range = True
        if "-" in numa_node_range:
            left, right = map(int, numa_node_range.split("-"))
            if left >= right or left < 0 or right < 0:
                print(
                    (
                        f'[WARNING] Incorrect provided numa node range: "{numa_node_range}". '
                        f"Proceeding without numa node range on numactl command line."
                    )
                )
                include_range = False
            elif right >= nb_numa_nodes:
                print(
                    (
                        f'[WARNING] Selected numa node range ("{numa_node_range}") '
                        f"is too large for the current platform "
                        f"(nb_numa_nodes = {nb_numa_nodes})."
                        f"Proceeding without numa node range on numactl command line."
                    )
                )
                include_range = False
        else:
            node_request = int(numa_node_range)
            if node_request < 0:
                print(
                    (
                        f'[WARNING] Incorrect provided node for numactl command: "{node_request}". '
                        f"Proceeding without numa node range on numactl command line."
                    )
                )
            elif node_request >= nb_numa_nodes:
                print(
                    (
                        f'[WARNING] Selected numa node for numactl ("{node_request}") '
                        f"is too large for the current platform "
                        f"(nb_numa_nodes = {nb_numa_nodes})."
                        f"Proceeding without numa node range on numactl command line."
                    )
                )
                include_range = False

        if include_range:
            numactl += ["-i", str(numa_node_range)]
    if numactl:
        numactl = ["numactl", "--all"] + numactl

    return numactl
