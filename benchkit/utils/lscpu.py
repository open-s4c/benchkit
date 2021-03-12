# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to interact with Linux utility "lscpu".

TODO move into helpers/linux.
"""

import json
import re
from typing import Optional, Tuple

from benchkit.communication import CommunicationLayer


def _gen_lscpu_dict(comm_layer: CommunicationLayer):
    lscpu_output = comm_layer.shell(
        command="lscpu -J",
        print_input=False,
        print_output=False,
    )
    lscpu_json = json.loads(lscpu_output)
    lscpu_dict = {e["field"]: e["data"] for e in lscpu_json["lscpu"]}

    return lscpu_dict


class LsCpu:
    """
    To interact with lscpu on the target host.
    """

    def __init__(
        self,
        comm_layer: CommunicationLayer,
    ):
        self._info_dict = _gen_lscpu_dict(comm_layer=comm_layer)

    def get(self, key: str) -> str:
        """
        Return the value of the given key in the lscpu output.

        Args:
            key (str): requested key.

        Returns:
            str: the value of the given key in the lscpu output.
        """
        return self._info_dict[key]

    def hyperthreads_per_core(self) -> int:
        """
        Return the number of hypterthreads (or CPUs) per core.

        Returns:
            int: the number of hypterthreads (or CPUs) per core.
        """
        return int(self.get("Thread(s) per core:"))

    def numa_nodes(self) -> int:
        """
        Return the number of NUMA nodes.

        Returns:
            int: the number of NUMA nodes.
        """
        return int(self.get("NUMA node(s):").strip())

    def sockets(self) -> int:
        """
        Return the number of sockets (or packages).

        Returns:
            int: the number of sockets (or packages).
        """
        result = self.get("Socket(s):")
        return int(result.strip())

    def l1d_cache(self) -> int:
        """
        Return the size of the L1 data cache.

        Returns:
            int: the size of the L1 data cache.
        """
        return _cache_size(cache_str=self.get("L1d cache:"))

    def l1i_cache(self) -> int:
        """
        Return the size of the L1 instruction cache.

        Returns:
            int: the size of the L1 instruction cache.
        """
        return _cache_size(cache_str=self.get("L1i cache:"))

    def l2_cache(self) -> int:
        """
        Return the size of the L2 cache.

        Returns:
            int: the size of the L2 cache.
        """
        return _cache_size(cache_str=self.get("L2 cache:"))

    def l3_cache(self) -> int:
        """
        Return the size of the L3 cache.

        Returns:
            int: the size of the L3 cache.
        """
        return _cache_size(cache_str=self.get("L3 cache:"))


def _cache_size_with_instances(cache_str: str) -> Optional[Tuple[str, str, str]]:
    m = re.match(
        pattern=r"(\d+)\s+([A-Za-z0-9]+B)\s+\((\d+) instances\)",
        string=cache_str,
    )
    if m is None:
        return None

    value_str, unit_bytes, nb_instances_str = m.groups()
    return value_str, unit_bytes, nb_instances_str


def _cache_size_without_instance(cache_str: str) -> Optional[Tuple[str, str, str]]:
    m = re.match(
        pattern=r"(\d+)\s+([A-Za-z0-9]+B)\s*",
        string=cache_str,
    )
    if m is None:
        return None

    value_str, unit_bytes = m.groups()
    return value_str, unit_bytes, "1"


def _cache_size(cache_str: str) -> int:
    cachesize_triplet = _cache_size_with_instances(cache_str=cache_str)
    if cachesize_triplet is None:
        cachesize_triplet = _cache_size_without_instance(cache_str=cache_str)
    if cachesize_triplet is None:
        raise ValueError(f'Fail to understand cache size value: "{cache_str}"')

    value_str, unit_bytes, nb_instances_str = cachesize_triplet

    unit = unit_bytes[:-1]

    unit2values = {
        "Ki": 2**10,
        "Mi": 2**20,
        "Gi": 2**30,
        "K": 10**3,
        "M": 10**6,
        "G": 10**9,
    }

    value = (int(value_str) * unit2values.get(unit)) // int(nb_instances_str)

    return value
