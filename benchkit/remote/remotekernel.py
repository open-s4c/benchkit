# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
This module allows to run kernel-related experiments (i.e. experiments where variation in the kernel
such as build options, boot-time arguments, etc. are variables).
Notice that this does not use the "remote platform" abstraction but instead directly use the
communication layer module and runs a remote tmux session that is controlled from the the host local
by benchkit.
"""

import pathlib
import subprocess
import time
from typing import List

from benchkit.communication import SSHCommLayer
from benchkit.helpers.linux.grubentries import set_grub_default
from benchkit.helpers.linux.kernel import Kernel
from benchkit.remote import TmuxSSHSession


class RemoteKernelExperiment:
    """
    Represent an experiment for a kernel running remotely.
    """

    def __init__(
        self,
        host: str,
        user: str,
        tmux_session_name: str,
        tmux_session_dir: str,
    ):
        self._host = host
        self._user = user
        self._tmux_session_name = tmux_session_name
        self._tmux_session_dir = pathlib.Path(tmux_session_dir)

        self._comm_layer = SSHCommLayer(host=host, environment=None)
        self._tmux_remote_session = None

    @property
    def tmux_remote_session(self) -> TmuxSSHSession:
        """
        Get the tmux remote session handle.

        Returns:
            TmuxSSHSession: the tmux remote session handle.
        """
        if self._tmux_remote_session is None or not self._tmux_remote_session.has_session(
            self._tmux_session_name
        ):
            self._tmux_remote_session = TmuxSSHSession(
                user=self._user,
                hostname=self._host,
                tmux_session_name=self._tmux_session_name,
                tmux_session_dir=str(self._tmux_session_dir),
                new_session_commands=[],
            )
            time.sleep(1)
        return self._tmux_remote_session

    def current_kernel_version(self) -> str:
        """
        Get the kernel version currently running on the remote host.

        Returns:
            str: the kernel version currently running on the remote host.
        """
        result = self._comm_layer.shell(command="uname -r").strip()
        return result

    def create_venv(self) -> None:
        """
        Create a venv on the remote kernel using configure.sh benchkit script.
        """
        venv_path = self._tmux_session_dir / "venv"
        venv_exists = self._comm_layer.path_exists(venv_path)
        if not venv_exists:
            self.run_command_wait_success(
                command="./configure.sh",
                seconds_before_wait_prompt=30,
            )

    def reboot_into_grub_id(
        self,
        grub_id: str,
        kernel_suffix: str,
    ) -> None:
        """
        Reboot the remote platform and run the kernel menu entry in grub corresponding to the given
        grub id.

        Args:
            grub_id (str): the grub menu id corresponding to the kernel to boot into.
            kernel_suffix (str): suffix of the kernel (for log messages).
        """
        print(f'[INFO] Configuring kernel "{kernel_suffix}" for next boot')
        set_grub_default(default_id=grub_id, comm_layer=self._comm_layer)
        self._comm_layer.shell(command="sudo update-grub")
        print(f'[INFO] Rebooting into kernel "{kernel_suffix}"')
        self._reboot_target()
        time.sleep(10)

    def reboot_into(self, kernel: Kernel) -> None:
        """
        Reboot the remote platform and boot the given kernel.

        Args:
            kernel (Kernel): the kernel to boot into.
        """
        target_kernel_grub_id = kernel.grub_menu_id
        self.reboot_into_grub_id(
            grub_id=target_kernel_grub_id,
            kernel_suffix=kernel.suffix,
        )

    def wait_boot_completed(self) -> None:
        """
        Wait for the remote platform to finish the boot process.
        """
        server_touched = False
        while not server_touched:
            try:
                self._comm_layer.shell(command="echo touch", timeout=5)
                server_touched = True
                continue
            except subprocess.TimeoutExpired:
                pass
            except subprocess.CalledProcessError as err:
                if 255 != err.returncode:
                    raise err
            print("[INFO] Unable to reach target server. Retrying in 60 seconds.")
            server_touched = False
            time.sleep(60)

    def run_command_wait_success(
        self,
        command: str,
        seconds_before_wait_prompt: int | None = None,
    ) -> None:
        """
        Run the given command on the remote platform and wait for it to succeed.

        Args:
            command (str): command to run on the remote platform.
            seconds_before_wait_prompt (int | None, optional): if not None, wait that time before
            trying to wait for a prompt on a tmux session of the remote. Defaults to None.
        """
        remote_session = self.tmux_remote_session

        remote_session.wait_prompt(sleep_interval_seconds=2)
        remote_session.run_command(command=command)
        if seconds_before_wait_prompt is not None:
            time.sleep(seconds_before_wait_prompt)
        remote_session.wait_prompt(sleep_interval_seconds=60)
        self.check_status(command=command)

    def check_status(
        self,
        command: str = "",
    ) -> None:
        """
        Check the status of the currently running command.

        Args:
            command (str, optional):
                currently executing command (useful to provide it for logging).
                Defaults to "".

        Raises:
            ValueError: if the last command in the tmux session failed.
        """
        remote_session = self.tmux_remote_session
        status = remote_session.get_status()
        if 0 != status:
            command_str = f' "{command}" ' if command else " "
            raise ValueError(
                f"Last command{command_str}failed in tmux session with status {status}"
            )

    def wait_experiment_completed(self, wait_interval_seconds: int = 60) -> None:
        """
        Wait for the experiment to be completed.

        Args:
            wait_interval_seconds (int, optional):
                interval (in seconds) between two pokes of the remote tmux session. Defaults to 60.
        """
        remote_session = self.tmux_remote_session
        remote_session.wait_prompt(sleep_interval_seconds=wait_interval_seconds)
        self.check_status()

    def filter_out_done_kernels(self, kernels_to_run: List[Kernel]) -> List[Kernel]:
        """
        Filter the kernels that already ran in the experiments from the given list.

        Args:
            kernels_to_run (List[Kernel]):
                the lists of all kernels to run in the experiments (including the ones for which the
                experiment already completed).

        Returns:
            List[Kernel]: the list of kernels to run for the experiments that are not executed yet.
        """
        current_kernel_version = self.current_kernel_version()
        if current_kernel_version.endswith("+"):
            current_kernel_version = current_kernel_version[:-1]

        current_kernel_idx = None
        for i, kernel in enumerate(kernels_to_run, start=0):
            if current_kernel_version.endswith(kernel.suffix):
                current_kernel_idx = i
                break

        if current_kernel_idx is None:
            return kernels_to_run

        return kernels_to_run[current_kernel_idx + 1 :]

    def _reboot_target(self):
        self._comm_layer.shell(command="sudo reboot", ignore_ret_codes=[255])
