# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to create custom Platforms (with manual specification of parameters of the deep memory
hierarchy).
"""

from typing import Optional

from .generic import Platform


def _compare_results(super_value: Optional[int], self_value: int, name: str) -> int:
    if super_value is not None and super_value != self_value:
        raise ValueError(
            f"{name} value provided in custom platform " "does not match system retrieved value"
        )
    return self_value


class CustomPlatform(Platform):
    """
    Fully customized platform where every parameter of the memory hierarchy is provided.
    """

    def __init__(
        self,
        nb_packages: int,
        nb_nodes: int,
        nb_caches: int,
        nb_cores: int,
        nb_cpus: int,
        cacheline_size: int,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self._nb_packages = nb_packages
        self._nb_nodes = nb_nodes
        self._nb_caches = nb_caches
        self._nb_cores = nb_cores
        self._nb_cpus = nb_cpus
        self._cacheline_size = cacheline_size

    def nb_cpus(self) -> int:
        """Return number of CPUs."""
        return _compare_results(
            super_value=super().nb_cpus(),
            self_value=self._nb_cpus,
            name="nb_cpus",
        )

    def nb_hyperthreaded_cores(self) -> int:
        """Return the number of hyperthreaded cores."""
        return _compare_results(
            super_value=super().nb_hyperthreaded_cores(),
            self_value=self._nb_cores,
            name="nb_cores",
        )

    def nb_cache_partitions(self) -> int:
        """Return the number of cache partitions."""
        return _compare_results(
            super_value=super().nb_cache_partitions(),
            self_value=self._nb_caches,
            name="nb_caches",
        )

    def nb_numa_nodes(self) -> int:
        """Return the number of NUMA nodes."""
        return _compare_results(
            super_value=super().nb_numa_nodes(),
            self_value=self._nb_nodes,
            name="nb_nodes",
        )

    def nb_packages(self) -> int:
        """Return the number of packages (or sockets)."""
        return _compare_results(
            super_value=super().nb_packages(),
            self_value=self._nb_packages,
            name="nb_packages",
        )

    def cache_line_size(self) -> int:
        """Return the size of a cache line."""
        return _compare_results(
            super_value=super().cache_line_size(),
            self_value=self._cacheline_size,
            name="cacheline_size",
        )
