# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Instances of Platform that represent various server processor models.
"""


from .generic import Platform


class GigabyteAMDEPYC7352c24x2(Platform):
    """Gigabyte AMD EPYC 7352, 2x 24 core processors (96 CPUs)"""

    def __init__(
        self,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

    @staticmethod
    def machine_ref() -> str:
        """Reference of the machine."""
        return "https://www.gigabyte.com/Rack-Server/R182-Z91-rev-100"

    @staticmethod
    def processor_ref() -> str:
        """Reference of the processor model."""
        return "https://www.amd.com/en/products/cpu/amd-epyc-7352"

    @staticmethod
    def processor_desc() -> str:
        """Description of the processor."""
        return "EPYC 7352 processors, an AMD chip with 24 x86_64 cores"

    @staticmethod
    def nominal_freq_desc() -> str:  # running at a nominal XXX frequency
        """Nominal frequency of the processor."""
        return "2.3 GHz"

    @staticmethod
    def denoted() -> str:
        """Notation of the platform."""
        return "gigabyte-96c"

    def machine_desc(self) -> str:
        """Description of the machine."""
        return (
            f"a GIGABYTE R182-Z91-00 rack server that has 128 GB of RAM "
            f"and 2x {self.processor_desc()}, "
            f"totaling 48 cores (96 CPUs when counting hyperthreading)"
        )

    def nb_hyperthreads_per_core(self) -> int:
        """Return the number of hyperthreads (or CPUs) per core."""
        return self.nb_cpus() // self.nb_hyperthreaded_cores()

    def nb_cpus(self) -> int:
        """Return number of CPUs."""
        return 96

    def nb_hyperthreaded_cores(self) -> int:
        """Return the number of hyperthreaded cores."""
        return 48

    def nb_cache_partitions(self) -> int:
        """Return the number of cache partitions."""
        return 16

    def nb_numa_nodes(self) -> int:
        """Return the number of NUMA nodes."""
        return 2

    def nb_packages(self) -> int:
        """Return the number of packages (or sockets)."""
        return 2


class GigabyteIntelXeonGold5222x2(Platform):
    """Gigabyte Intel Xeon Gold 5222, 2x 4 cores (16 CPUs)"""

    def __init__(
        self,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

    def nb_hyperthreads_per_core(self) -> int:
        """Return the number of hyperthreads (or CPUs) per core."""
        return self.nb_cpus() // self.nb_hyperthreaded_cores()

    def nb_cpus(self) -> int:
        """Return number of CPUs."""
        return 16

    def nb_hyperthreaded_cores(self) -> int:
        """Return the number of hyperthreaded cores."""
        return 8

    def nb_cache_partitions(self) -> int:
        """Return the number of cache partitions."""
        raise NotImplementedError

    def nb_numa_nodes(self) -> int:
        """Return the number of NUMA nodes."""
        return 2

    def nb_packages(self) -> int:
        """Return the number of packages (or sockets)."""
        return 2


class Huawei2288XIntelXeonGold6266Cx2(Platform):
    """Huawei 2288X Intel Xeon Gold 6266C, 2x 22 cores (88 CPUs)"""

    def __init__(
        self,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

    def nb_hyperthreads_per_core(self) -> int:
        """Return the number of hyperthreads (or CPUs) per core."""
        return self.nb_cpus() // self.nb_hyperthreaded_cores()

    def nb_cpus(self) -> int:
        """Return number of CPUs."""
        return 88

    def nb_hyperthreaded_cores(self) -> int:
        """Return the number of hyperthreaded cores."""
        return 44

    def nb_cache_partitions(self) -> int:
        """Return the number of cache partitions."""
        raise NotImplementedError

    def nb_numa_nodes(self) -> int:
        """Return the number of NUMA nodes."""
        return 2

    def nb_packages(self) -> int:
        """Return the number of packages (or sockets)."""
        return 2


class Taishan200Kunpeng9206426x2(Platform):
    """Taishan 200 Kunpeng 920 6426, 2x 64 cores (128 CPUs)."""

    def __init__(
        self,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

    @staticmethod
    def machine_ref() -> str:
        """Reference of the machine."""
        return "https://e.huawei.com/uk/products/servers/taishan-server/taishan-2280-v2"

    @staticmethod
    def processor_ref() -> str:
        """Reference of the processor model."""
        return "https://en.wikichip.org/wiki/hisilicon/kunpeng/920-6426"

    @staticmethod
    def processor_desc() -> str:
        """Description of the processor."""
        return "Kunpeng 920-6426 processors, a HiSilicon chip with 64 ARMv8.2 64-bit cores"

    @staticmethod
    def nominal_freq_desc() -> str:  # running at a nominal XXX frequency
        """Nominal frequency of the processor."""
        return "2.6 GHz"

    @staticmethod
    def denoted() -> str:
        """Notation of the platform."""
        return "taishan200-128c"

    def machine_desc(self) -> str:
        """Description of the machine."""
        return (
            f"a Huawei TaiShan 200 (Model 2280) rack server that has 128 GB of RAM and "
            f"2x {self.processor_desc()} totaling 128 cores (no SMT)"
        )

    def nb_hyperthreads_per_core(self) -> int:
        """Return the number of hyperthreads (or CPUs) per core."""
        return self.nb_cpus() // self.nb_hyperthreaded_cores()

    def nb_cpus(self) -> int:
        """Return number of CPUs."""
        return 128

    def nb_hyperthreaded_cores(self) -> int:
        """Return the number of hyperthreaded cores."""
        return 128

    def nb_cache_partitions(self) -> int:
        """Return the number of cache partitions."""
        return 32

    def nb_numa_nodes(self) -> int:
        """Return the number of NUMA nodes."""
        return 4

    def nb_packages(self) -> int:
        """Return the number of packages (or sockets)."""
        return 2


class Taishan200Kunpeng9204826x2(Platform):
    """Taishan 200 Kunpeng 920 4826, 2x 48 cores (96 CPUs)."""

    def __init__(
        self,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)

    @staticmethod
    def machine_ref() -> str:
        """Reference of the machine."""
        return "https://e.huawei.com/uk/products/servers/taishan-server/taishan-2280-v2"

    @staticmethod
    def processor_ref() -> str:
        """Reference of the processor model."""
        return "https://en.wikichip.org/wiki/hisilicon/kunpeng/920-4826"

    @staticmethod
    def processor_desc() -> str:
        """Description of the processor."""
        return "Kunpeng 920-4826 processors, a HiSilicon chip with 48 ARMv8.2 64-bit cores"

    @staticmethod
    def nominal_freq_desc() -> str:  # running at a nominal XXX frequency
        """Nominal frequency of the processor."""
        return "2.6 GHz"

    @staticmethod
    def denoted() -> str:
        """Notation of the platform."""
        return "taishan200-96c"

    def machine_desc(self) -> str:
        """Description of the machine."""
        return (
            f"a Huawei TaiShan 200 (Model 2280) rack server that has 128 GB of RAM and "
            f"2x {self.processor_desc()} totaling 96 cores (no SMT)"
        )

    def nb_hyperthreads_per_core(self) -> int:
        """Return the number of hyperthreads (or CPUs) per core."""
        return self.nb_cpus() // self.nb_hyperthreaded_cores()

    def nb_cpus(self) -> int:
        """Return number of CPUs."""
        return 96

    def nb_hyperthreaded_cores(self) -> int:
        """Return the number of hyperthreaded cores."""
        return 96

    def nb_cache_partitions(self) -> int:
        """Return the number of cache partitions."""
        return 24

    def nb_numa_nodes(self) -> int:
        """Return the number of NUMA nodes."""
        return 4

    def nb_packages(self) -> int:
        """Return the number of packages (or sockets)."""
        return 2
