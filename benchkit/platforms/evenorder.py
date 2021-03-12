# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Generate the even CPU order on any given platform memory hierarchy.
TODO typing in this file.
"""

from typing import List


def _get_hierarchy(
    nb_cpus,
    nb_cache_partitions,
    nb_numa_nodes,
    nb_packages,
):  # TODO return type
    cpus_per_cache_partitions = nb_cpus // nb_cache_partitions
    cache_partitions_per_numa_node = nb_cache_partitions // nb_numa_nodes
    numa_nodes_per_package = nb_numa_nodes // nb_packages

    cpus = list(range(nb_cpus))
    cache_partitions = [
        cpus[i : i + cpus_per_cache_partitions]
        for i in range(0, nb_cpus, cpus_per_cache_partitions)
    ]
    numa_nodes = [
        cache_partitions[i : i + cache_partitions_per_numa_node]
        for i in range(0, nb_cache_partitions, cache_partitions_per_numa_node)
    ]
    packages = [
        numa_nodes[i : i + numa_nodes_per_package]
        for i in range(0, nb_numa_nodes, numa_nodes_per_package)
    ]
    return packages


def _level_count(hierarchy) -> int:
    if len(hierarchy) == 0:
        return 0
    if not isinstance(hierarchy[0], list):
        return len(hierarchy)
    return sum(map(_level_count, hierarchy))


def _next_value(hierarchy):  # TODO return value
    if len(hierarchy) == 0:
        raise ValueError("No more value at this level")
    if not isinstance(hierarchy[0], list):
        result = hierarchy.pop()
        return result
    count2sublevel = [_level_count(h) for h in hierarchy]
    max_count = max(count2sublevel)
    min_count = min(count2sublevel)

    if max_count == min_count:
        return _next_value(hierarchy[-1])
    if len(hierarchy) <= 2:
        return _next_value(hierarchy[0])

    # Below we have len(hierarchy) > 2
    for i in range(len(count2sublevel) - 1, -1, -1):
        if count2sublevel[i] == max_count:
            return _next_value(hierarchy[i])

    return -1  # TODO manage this edge case, probably unreachable


def get_order(
    nb_cpus: int,
    nb_cache_partitions: int,
    nb_numa_nodes: int,
    nb_packages: int,
    nb_hyperthreads_per_core: int,
) -> List[int]:
    """Get even CPU order given the description of the memory hierarchy.
    The even CPU order means that each adjacent thread will be scheduled as far
    as each other possible on the platform.
    Computer motherboards have a number of socket, each can hold a *package*.
    A *package* will contain one or several *NUMA nodes*.
    A *NUMA node* will contain several cache partitions or *cache groups*.
    A *cache group* will contain several *cores*.
    Finally, a *core* can contain either one *CPU*, or several in case of
    hyperthreading/SMT is enabled.

    Args:
        nb_cpus (int): total number of CPUs.
        nb_cache_partitions (int): number of cache groups.
        nb_numa_nodes (int): number of NUMA nodes.
        nb_packages (int): number of packages.
        nb_hyperthreads_per_core (int): number of hyperthreads (= CPUs) per core.

    Returns:
        List[int]: the cpu ordering, ordered in the "even" distribution, meaning each adjacent
        thread will be as far from each other as possible.
    """
    nb_cores = nb_cpus // nb_hyperthreads_per_core
    top_level_hierarchy = _get_hierarchy(
        nb_cpus=nb_cores,
        nb_cache_partitions=nb_cache_partitions,
        nb_numa_nodes=nb_numa_nodes,
        nb_packages=nb_packages,
    )
    order_1_hyperthread = [_next_value(hierarchy=top_level_hierarchy) for _ in range(nb_cores)]

    # we replicate the 1-hyperthread version of the order, but we update the core id
    order_all_hyperthreads = sum(
        [
            [e + (nb_cores * i) for e in order_1_hyperthread]
            for i in range(nb_hyperthreads_per_core)
        ][::-1],
        [],  # start argument is an empty list
    )

    return order_all_hyperthreads
