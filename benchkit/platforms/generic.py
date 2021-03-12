# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module for the representation of generic platforms that can be derived into actual platforms.
"""

from typing import List

from benchkit.communication import CommunicationLayer
from benchkit.platforms import evenorder
from benchkit.platforms.utils import (
    get_nb_cpus_active,
    get_nb_cpus_isolated,
    get_nb_cpus_total,
)
from benchkit.utils import lscpu


class Platform:
    """
    Represent a generic platform with all the supported calls, including the communication layer.
    """

    def __init__(
        self,
        comm_layer: CommunicationLayer,
    ) -> None:
        self._comm_layer = comm_layer
        self.hostname = self._comm_layer.hostname()
        self._architecture = None
        self._lscpu = None
        self._nb_hyperthreads_per_core = None

    @property
    def comm(self) -> CommunicationLayer:
        """
        Get the communication layer of the host associated with the current platform.

        Returns:
            CommunicationLayer:
                the communication layer of the host associated with the current platform.
        """
        return self._comm_layer

    def _get_lscpu(self) -> lscpu.LsCpu:
        if self._lscpu is None:
            self._lscpu = lscpu.LsCpu(comm_layer=self.comm)
        return self._lscpu

    def nb_cpus_per_cache_partition(self) -> int:
        """
        Get the number of CPUs in one cache partition (or cache group).

        Returns:
            int: the number of CPUs in one cache partition (or cache group).
        """
        return self.nb_cpus() // self.nb_cache_partitions()

    def nb_cache_partition_per_numa_node(self) -> int:
        """
        Get the number of cache partitions (or cache groups) in one NUMA node.

        Returns:
            int: the number of cache partitions (or cache groups) in one NUMA node.
        """
        return self.nb_cache_partitions() // self.nb_numa_nodes()

    def nb_cpus_per_numa_node(self) -> int:
        """
        Get the number of CPUs in one NUMA node.

        Returns:
            int: the number of CPUs in one NUMA node.
        """
        return self.nb_cpus() // self.nb_numa_nodes()

    def nb_cpus_per_package(self) -> int:
        """
        Get the number of CPUs in one package.

        Returns:
            int: the number of CPUs in one package.
        """
        return self.nb_cpus() // self.nb_packages()

    def nb_hyperthreads_per_core(self) -> int:
        """
        Get the number of hyperthreads (or CPUs) per core.

        Returns:
            int: the number of hyperthreads (or CPUs) per core.
        """
        if self._nb_hyperthreads_per_core is None:
            self._nb_hyperthreads_per_core = self._get_lscpu().hyperthreads_per_core()
        return self._nb_hyperthreads_per_core

    @property
    def architecture(self) -> str:
        """
        Get the architecture of the platform.

        Returns:
            str: the architecture of the platform.
        """
        if self._architecture is None:
            self._architecture = self.comm.shell(
                "uname -m",
                print_input=False,
                print_output=False,
            ).strip()
        return self._architecture

    def nb_cpus(self) -> int:
        """
        Get the total number of CPUs of the platform.
        It represents the number of "hyperthreads" in the system, i.e. the amount of CPUs visible
        by the operating system.

        Returns:
            int: the total number of CPUs of the platform.
        """
        result = get_nb_cpus_total(comm_layer=self.comm)
        return result

    def nb_active_cpus(self) -> int:
        """
        Get the number of CPUs of the platform that are active (not isolated).

        Returns:
            int: the number of CPUs of the platform that are active (not isolated).
        """
        # does not count the isolated CPUs in the count
        result = get_nb_cpus_active(comm_layer=self.comm)
        return result

    def nb_isolated_cpus(self) -> int:
        """
        Get the number of CPUs of the platform that are isolated (not active).

        Returns:
            int: the number of CPUs of the platform that are isolated (not active).
        """
        # does *only* count the isolated CPUs in the count
        result = get_nb_cpus_isolated(comm_layer=self.comm)
        return result

    def nb_hyperthreaded_cores(self) -> int:
        """
        Get the number of cores (possibly hyperthreaded) of the platform.
        For example, on x86_64, there are 2 CPUs per core (or 2 hyperthread per core).
        On Armv8, there is no SMT (no hyperthreading), so there is 1 CPU per core.
        On Armv8, we have nb_hyperthreaded_cores() == nb_cpus().

        Returns:
            int: the number of cores of the platform, possibly hyperthreaded.
        """
        result = self.nb_cpus() // self.nb_hyperthreads_per_core()
        return result

    def nb_cache_partitions(self) -> int:
        """
        Get the total number of cache partitions (or cache groups) of the platform.

        Returns:
            int: _description_
        """
        # conservative assumption in the absence of the precise information:
        return self.nb_hyperthreaded_cores()

    def nb_numa_nodes(self) -> int:
        """
        Get the total number of NUMA nodes of the platform.

        Returns:
            int: the total number of NUMA nodes of the platform.
        """
        return self._get_lscpu().numa_nodes()

    def nb_packages(self) -> int:
        """
        Get the total number of packages (or sockets) of the platform.

        Returns:
            int: the total number of packages (or sockets) of the platform.
        """
        return self._get_lscpu().sockets()

    def cache_line_size(self) -> int | None:
        """
        Get the size (in bytes) of one cache line on the platform.
        It returns None if this information is not known.

        Returns:
            int | None: the size (in bytes) of one cache line on the platform.
        """
        return None  # unknown at this stage

    def cpu_order(
        self,
        provided_order: str | List[int] = "asc",  # TODO use the CpuOrder type
    ) -> List[int]:
        """
        Provide the list of CPU identifiers in the order matching the given specified CPU order.
        For example, if the provided order is "asc" on a platform with 4 cores, the result will be
        [0, 1, 2, 3]. If the provided order is "desc", the result will be [3, 2, 1, 0], etc.

        Args:
            provided_order (str | List[int], optional):
                Specification of the CPU order. Defaults to "asc".

        Raises:
            NotImplementedError: if the specified order is not recognized.

        Returns:
            List[int]: list of CPU identifiers of the platform matching the specified CPU order.
        """
        if not isinstance(provided_order, str):
            if all(isinstance(cid, int) for cid in provided_order):
                # if the provided order is a list of integer core id, returns it
                # as the selected cpu_order.
                return provided_order

        nb_cpus = self.nb_cpus()

        match provided_order:
            case "even":
                result_ordering = self.cpu_order_even()
            case "desc":
                result_ordering = list(range(nb_cpus - 1, -1, -1))
            case "asc":
                result_ordering = list(range(1, nb_cpus, 1)) + [0]
            case _:
                raise NotImplementedError(f"Unknown core ordering technique: {provided_order}")

        return result_ordering

    def master_thread_core_id(self, cpu_order_list: List[int]) -> int:
        """
        Given a list of CPU identifiers that will be a thread-to-core assignment, return on what
        core should the main thread (first thread to start the process) be executed.
        Ensuring the first thread runs on that core usually yield better performance, as the memory
        allocation policy will be based on where is the main thread currently executing (as the
        main thread is usually in charge of allocating memory for the other threads).
        We selected the following policy: the allocator thread should be the first one of the NUMA
        node of thread with tid 1 (the second thread to be created).

        Args:
            cpu_order_list (List[int]):
                given order of CPU identifiers for a thread-to-core assignment.

        Returns:
            int: where the main thread should be running.
        """
        tid1_cid = cpu_order_list[0]
        nb_cpus_per_numa_node = self.nb_cpus_per_numa_node()

        # we remove the "modulo" index inside the numa node:
        tid0_cid = (tid1_cid // nb_cpus_per_numa_node) * nb_cpus_per_numa_node

        return tid0_cid

    def cpu_order_even(self) -> List[int]:
        """
        Provide the "even" distribution of threads on the current platform.
        This means that two "adjacent" threads (thread created one after the other) will be
        scheduled as far from each other as possible.
        This CPU order distribution is especially useful when one desire to measure the
        cross-package and cross-NUMA nodes latencies.

        Returns:
            List[int]:
                list of CPU identifiers corresponding to the even distribution on the current
                platform.
        """
        ordering = evenorder.get_order(
            nb_cpus=self.nb_cpus(),
            nb_cache_partitions=self.nb_cache_partitions(),
            nb_numa_nodes=self.nb_numa_nodes(),
            nb_packages=self.nb_packages(),
            nb_hyperthreads_per_core=self.nb_hyperthreads_per_core(),
        )
        return ordering

    def kernel_version(self) -> str:
        """
        Identifier of the kernel ("uname -r") running currently on the platform.

        Returns:
            str: identifier of the kernel running currently on the platform.
        """
        output = self.comm.shell(command="uname -r", print_output=False)
        result = output.strip()
        return result

    def current_user(self) -> str:
        """
        Get the name of the current user logged in the platform.

        Returns:
            str: the name of the current user logged in the platform.
        """
        return self.comm.current_user()
