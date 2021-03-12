# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Instances of Platform that represent various workstations.
"""

from .generic import Platform


class AMDRyzen536006C(Platform):
    """AMD Ryzen 5 3600, 6 cores (12 CPUs)"""

    def __init__(
        self,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

    def nb_cpus(self) -> int:
        """Return number of CPUs."""
        return 12

    def nb_hyperthreaded_cores(self) -> int:
        """Return the number of hyperthreaded cores."""
        return 6

    def nb_cache_partitions(self) -> int:
        """Return the number of cache partitions."""
        return 2

    def nb_numa_nodes(self) -> int:
        """Return the number of NUMA nodes."""
        return 1

    def nb_packages(self) -> int:
        """Return the number of packages (or sockets)."""
        return 1


class WorkstationIntelXeonW2133(Platform):
    """Intel Xeon W2133, 6 cores (12 CPUs)."""

    def __init__(
        self,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

    def nb_cpus(self) -> int:
        """Return number of CPUs."""
        return 12

    def nb_hyperthreaded_cores(self) -> int:
        """Return the number of hyperthreaded cores."""
        return 6

    def nb_cache_partitions(self) -> int:
        """Return the number of cache partitions."""
        return 1

    def nb_numa_nodes(self) -> int:
        """Return the number of NUMA nodes."""
        return 1

    def nb_packages(self) -> int:
        """Return the number of packages (or sockets)."""
        return 1


class HuaweiMatebookXPro(Platform):
    """Represent a subset of the CPUs of a Huawei MatebookX Pro laptop."""

    def __init__(
        self,
        configure_nb_cpus: int = 4,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._nb_cpus = configure_nb_cpus

    def nb_cpus(self) -> int:
        """Return number of CPUs."""
        return self._nb_cpus

    def nb_hyperthreaded_cores(self) -> int:
        """Return the number of hyperthreaded cores."""
        return self._nb_cpus

    def nb_cache_partitions(self) -> int:
        """Return the number of cache partitions."""
        return 1

    def nb_numa_nodes(self) -> int:
        """Return the number of NUMA nodes."""
        return 1

    def nb_packages(self) -> int:
        """Return the number of packages (or sockets)."""
        return 1
