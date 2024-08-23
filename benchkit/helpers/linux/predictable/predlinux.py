# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Useful tools and configurations to reduce unpredictability of Linux and
"stabilize" the target platform.
"""

import os.path
from typing import Optional

from benchkit.helpers.linux import sysctl
from benchkit.helpers.linux.predictable.cpupower import CPUPower
from benchkit.helpers.linux.predictable.systemctl import Systemctl
from benchkit.platforms import Platform, get_current_platform


class PredLinuxError(Exception):
    """Errors with predictable linux tool."""


class PredLinux:
    """Main class to set predictable linux configuration."""

    def __init__(
        self,
        platform: Platform | None = None,
    ):
        self._platform = platform if platform is not None else get_current_platform()
        self._systemctl = Systemctl(comm_layer=self._platform.comm)

    def predverifydo(
        self,
        change_frequency: bool = True,
        expected_nb_isolated_cpus: Optional[int] = None,
        bypass_isolation_check: bool = False,
    ) -> None:
        """Check whether all predictable settings are effectively set.

        Args:
            change_frequency (bool, optional):
                change the frequency if it is not set to the expected predictable value.
                Defaults to True.
            expected_nb_isolated_cpus (Optional[int], optional):
                expected number of isolated CPUs. If None, assume that all CPUs are isolated but
                one. Defaults to None.
            bypass_isolation_check (bool, optional):
                if true, do not check that CPUs are isolated. Defaults to False.
        """
        self.check_irqbalance()
        self.check_numabalance()
        self.check_isolcpus(
            expected_nb_isolated_cpus=expected_nb_isolated_cpus,
            bypass_isolation_check=bypass_isolation_check,
        )
        if change_frequency:
            self.set_low_freq()
        self.set_softlockuptimeout()

    def preddo(
        self,
        frequency_to_set: Optional[int] = 1500,
        expected_nb_isolated_cpus: Optional[int] = None,
        bypass_isolation_check: bool = False,
    ) -> None:
        """Set effective configuration to be predictable. Isolating the CPU cannot be set as it is
        a boot-time parameter.

        Args:
            frequency_to_set (Optional[int], optional):
                Frequency to set to all CPUs, in MHz. Defaults to 1500.
            expected_nb_isolated_cpus (Optional[int], optional):
                expected number of isolated CPUs. If None, assume that all CPUs are isolated but
                one. Defaults to None.
            bypass_isolation_check (bool, optional):
                if true, do not check that CPUs are isolated. Defaults to False.
        """
        self.stop_irqbalance()
        self.stop_numabalance()
        self.check_isolcpus(
            expected_nb_isolated_cpus=expected_nb_isolated_cpus,
            bypass_isolation_check=bypass_isolation_check,
        )
        if frequency_to_set is not None:
            self.set_low_freq(frequency_mhz=frequency_to_set)
        self.set_softlockuptimeout()

    def check_irqbalance(self) -> None:
        """
        Check whether irqbalance is disabled
        """
        if self._systemctl.is_active("irqbalance"):
            raise PredLinuxError(
                (
                    "Error: IRQ balancer daemon is not disabled. "
                    "Please disable it by executing the following: "
                    "sudo systemctl stop irqbalance"
                )
            )

    def stop_irqbalance(self):
        """
        Disable irqbalance daemon for this boot
        """
        if self._systemctl.is_active("irqbalance"):
            self._systemctl.stop("irqbalance")

    def check_numabalance(self) -> None:
        """
        Check whether NUMA balancing is disabled.
        To disable even after reboot, add the following line to '/etc/sysctl.conf':
          kernel.numa_balancing=0
        """
        numabalance_path = "/proc/sys/kernel/numa_balancing"
        if not self._platform.comm.isfile(path=numabalance_path):
            return  # numa balance not available on this platform, check not required.

        numa_balance_filecontent = self._platform.comm.read_file(path=numabalance_path).strip()

        numa_balance_status = int(numa_balance_filecontent)

        if 0 != numa_balance_status:
            raise PredLinuxError(
                (
                    "Error: NUMA balancer is not disabled. Please disable it. "
                    'To do this for all reboots, add the following line to "/etc/sysctl.conf": '
                    '"kernel.numa_balancing=0" and then reboot. '
                    "To do this temporarily, run the following command: "
                    '"sudo sysctl kernel.numa_balancing=0"'
                )
            )

    def stop_numabalance(self):
        """
        Disable numabalance daemon for this boot
        """
        numabalance_path = "/proc/sys/kernel/numa_balancing"
        if not self._platform.comm.isfile(path=numabalance_path):
            return  # numa balance not available on this platform, check not required.

        sysctl.write(
            variable="kernel.numa_balancing",
            value="0",
            comm_layer=self._platform.comm,
        )

    def check_isolcpus(
        self,
        expected_nb_isolated_cpus: Optional[int] = None,
        bypass_isolation_check: bool = False,
    ) -> None:
        """
        Check whether cpus are isolated.
        Isolation needs to be enabled via Linux boot argument with the "isolcpus=..." variable.
        """

        p = self._platform
        total_nb_cpus = p.nb_cpus()
        actual_nb_isolated_cpus = p.nb_isolated_cpus()

        if expected_nb_isolated_cpus is None:
            # "all but one" is assumed if the arg is not provided
            expected_nb_isolated_cpus = total_nb_cpus - 1

        if expected_nb_isolated_cpus != actual_nb_isolated_cpus:
            err_msg = (
                f"Error: CPUs are not isolated according to specification "
                f"(expected number of isolated CPUs: {expected_nb_isolated_cpus}, "
                f"actual number of isolated CPUs: {actual_nb_isolated_cpus}). "
                f'To isolate CPUs, use the kernel boot argument "isolcpus". '
                f'To change expected number, add parameter "expected_nb_isolated_cpus" to '
                "predverifydo call."
            )
            if bypass_isolation_check:
                print(f"[WARNING] {err_msg}")
            else:
                raise PredLinuxError(f"Error: {err_msg}")

    def set_low_freq(
        self,
        frequency_mhz: int = 1500,
    ) -> None:
        """Set a low frequency to all CPUs to avoid the thermal alarm to be triggered and skew the
        results. Specific care must be taken on x86 platforms, a command-line option must be given
        to the kernel, see
        https://unix.stackexchange.com/questions/153693/cant-use-userspace-cpufreq-governor-and-set-cpu-frequency

        Args:
            frequency_mhz (int, optional):
                frequency value to set to all CPUs, in MHz. Defaults to 1500.

        Raises:
            PredLinuxError:
                if the actual frequency after the set operation is not the requested frequency.
        """
        cpu_power = CPUPower(comm_layer=self._platform.comm)

        cpu_power.set_governor(governor="userspace")
        cpu_power.set_frequency(frequency_mhz=frequency_mhz)

        total_nb_cpus = self._platform.nb_cpus()
        for current_cpu in range(total_nb_cpus):
            current_freq = cpu_power.get_frequency_mhz(cpu=current_cpu)
            if frequency_mhz != current_freq:
                raise PredLinuxError(
                    (
                        f"CPU {current_cpu} frequency is {current_freq} MHz. "
                        f"Expected: {frequency_mhz} MHz."
                    )
                )
        print(f"[INFO] Successfully updated the frequency of all cores to {frequency_mhz} MHz.")

    def set_softlockuptimeout(self, timeout_value: int = 120) -> None:
        """
        Setting a high timeout to avoid soft lockup detection being false positives.
        """

        watchdog_file = "/proc/sys/kernel/watchdog_thresh"
        if not self._platform.comm.isfile(watchdog_file):
            return

        # The timeout is 2x the written value.
        # So the softlockup will be fired after 120 seconds in the default case.
        value_to_set = timeout_value // 2

        current_value = int(self._platform.comm.read_file(path=watchdog_file).strip())
        if value_to_set == current_value:
            return

        value_str = f"{value_to_set}\n"
        self._platform.comm.shell(
            command=f"sudo tee {watchdog_file}",
            std_input=value_str,
            print_input=False,
            print_output=False,
            shell=True,
        )


def main():
    """Example usage."""
    platform = get_current_platform()
    nb_cpus = platform.nb_cpus()

    pred = PredLinux()
    pred.predverifydo(expected_nb_isolated_cpus=nb_cpus - 1)


if __name__ == "__main__":
    main()
