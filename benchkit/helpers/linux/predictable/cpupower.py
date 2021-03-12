# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Handle `cpupower` tool to manipulate frequency and DVFS operating points
of the different CPUs of the target platform.
"""

import re
from typing import Iterable, Optional

from benchkit.communication import CommunicationLayer, LocalCommLayer


class CPUPower:
    """
    Object to run the `cpupower` tool and control frequency of the target platform.
    """

    def __init__(
        self,
        comm_layer: CommunicationLayer = LocalCommLayer(),
    ) -> None:
        self._comm_layer = comm_layer

    def set_governor(
        self,
        governor: str = "userspace",
        cpus: Optional[Iterable[int]] = None,
    ) -> None:
        """Set the given frequency governor on the given CPUs.

        Args:
            governor (str, optional):
                governor to set. Defaults to "userspace".
            cpus (Optional[Iterable[int]], optional):
                list of CPUs to which to set the governor. Defaults to None.
        """
        cpu_list = CPUPower._cpu_list(cpus=cpus)
        self._comm_layer.shell(
            command=f"sudo cpupower --cpu {cpu_list} frequency-set --governor {governor}",
            print_output=False,
        )

    def set_frequency(
        self,
        frequency_mhz: int,
        cpus: Optional[Iterable[int]] = None,
    ) -> None:
        """Set the given frequency to the given CPUs.

        Args:
            frequency_mhz (int):
                frequency to set, in MHz.
            cpus (Optional[Iterable[int]], optional):
                list of CPUs to which to set the frequency. Defaults to None.
        """
        cpu_list = CPUPower._cpu_list(cpus=cpus)
        self._comm_layer.shell(
            command=f"sudo cpupower --cpu {cpu_list} frequency-set --freq {frequency_mhz}MHz",
            print_output=False,
        )

    def get_frequency_mhz(
        self,
        cpu: int,
    ) -> int:
        """Get the frequency of the given CPU.

        Args:
            cpu (int): CPU identifier of the CPU to query.

        Raises:
            ValueError: if cpupower is not able to extract the frequency of the given CPU.

        Returns:
            int: frequency value of the given CPU, in MHz.
        """
        raw_output = self._comm_layer.shell(
            command=f"sudo cpupower --cpu {cpu} frequency-info",
            print_input=False,
            print_output=False,
        )
        output_lines = raw_output.strip().splitlines()
        frequency_lines = [
            line for line in output_lines if "current CPU frequency:" in line and "Hz" in line
        ]

        if not frequency_lines:
            raise ValueError("Unable to get frequency information from cpupower.")

        frequency_line = frequency_lines[0]

        m = re.match(
            pattern=r"\s+current CPU frequency:\s+(?P<value>[0-9.]+)\s+(?P<unit>\w+)\s+.*",
            string=frequency_line,
        )

        if m is None:
            raise ValueError(
                "Unable to extract frequency information from cpupower frequency line."
            )

        gd = m.groupdict()

        value = gd["value"]
        unit = gd["unit"]
        multiplier_unit = unit.split("Hz")[0]

        match multiplier_unit:
            case "":
                multiplier = 1
            case "K":
                multiplier = 10**3
            case "M":
                multiplier = 10**6
            case "G":
                multiplier = 10**9
            case _:
                raise ValueError(
                    f"Unable to identify the multiplier in frequency: {multiplier_unit}"
                )

        value_hz = int(float(value) * multiplier)
        value_mhz = value_hz // (10**6)

        return value_mhz

    @staticmethod
    def _cpu_list(cpus: Optional[Iterable[int]]) -> str:
        # If cpus aren't provided (None or empty Iterable), all CPUs are assumed
        cpu_list = "all" if cpus is None else ",".join([str(c) for c in cpus])
        return cpu_list
