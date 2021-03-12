# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Helpers to build Linux kernel.

Notice it does only support local build for now (no communication layer).
"""

import os
from typing import Dict, List, Tuple

import git
import wget

from benchkit.helpers.linux.distrib import get_distrib_id
from benchkit.helpers.linux.grubentries import KernelEntry, find_last_vanilla
from benchkit.shell.shell import pipe_shell_out, shell_out
from benchkit.utils.dir import parentdir
from benchkit.utils.misc import TimeMeasure
from benchkit.utils.types import PathType

# Linux kernel build option
Option = str

_DEFAULT_KERNEL_URL = "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git"


class LinuxBuild:
    """Helper to build Linux kernel."""

    def __init__(self, repo_path: PathType) -> None:
        self._repo_path = repo_path

    @staticmethod
    def from_git(
        repo_path: PathType,
        repo_url: str | None = None,  # commit ID or branch
        ref: str | None = None,
    ) -> "LinuxBuild":
        """Create an instance from a git URL, including cloning it.

        Args:
            repo_path (PathType):
                path where to clone the repo.
            repo_url (str | None, optional):
                URL of the git to clone from, if None, it clones Linus' tree. Defaults to None.
            ref (str | None):
                commit ID or branch name.

        Returns:
            LinuxBuild: a LinuxBuild instance pointing to the cloned repository.
        """
        if os.path.isdir(repo_path):
            repo = git.Repo(path=repo_path)
        else:
            if repo_url is None:
                repo_url = _DEFAULT_KERNEL_URL

            repo = git.Repo.clone_from(
                url=repo_url,
                to_path=repo_path,
            )

        if ref is not None:
            repo.git.checkout(ref)

        return LinuxBuild(repo_path=repo_path)

    @staticmethod
    def from_tarball(
        repo_path: PathType,
        tarball_dir: PathType,
        tarball_url: str,
    ) -> "LinuxBuild":
        """Create an instance from a tarball URL, including downloading it and decompressing it.

        Args:
            repo_path (PathType): path where to uncompress the kernel.
            tarball_dir (PathType): path where to download the tarball.
            tarball_url (str): URL to the tarball to download.

        Returns:
            LinuxBuild: a LinuxBuild instance pointing to the uncompressed tarball.
        """
        if not os.path.isdir(repo_path) and not os.path.exists(repo_path):
            os.makedirs(tarball_dir, exist_ok=True)
            tarball_path = wget.download(url=tarball_url, out=tarball_dir)
            shell_out(f"tar -xf {tarball_path}")

        return LinuxBuild(repo_path=repo_path)

    @staticmethod
    def _start_config_content(original_config_pathname: PathType | None = None) -> str:
        config_path = original_config_pathname

        if original_config_pathname is None:
            vanilla_kernel = find_last_vanilla()
            config_path = f"/boot/config-{vanilla_kernel}"
            if not os.path.isfile(config_path):
                raise ValueError(
                    f"Kernel build config file not found for " f'vanilla kernel: "{config_path}"'
                )

        with open(config_path, "r") as original_config_file:
            content = original_config_file.read()

        return content

    def config_enable_option(self, option: Option) -> None:
        """Enable the given option in the kernel configuration.

        Args:
            option (Option): name of the option to enable.
        """
        self._script_config(command="enable", option=option)

    def config_disable_option(self, option: Option) -> None:
        """Disable the given option in the kernel configuration.

        Args:
            option (Option): name of the option do disable.
        """
        self._script_config(command="disable", option=option)

    def config_set_string_option(
        self,
        option: Option,
        value: str,
    ) -> None:
        """Set a kernel configuration option whose value is a string.

        Args:
            option (Option): name of the option to set.
            value (str): value of the option to set.
        """
        self._script_config(command="set-str", option=option, value=value)

    def config_module_option(self, option: Option) -> None:
        """Set a kernel configuration option to be built as a kernel module.

        Args:
            option (Option): name of the option to set as a kernel module.
        """
        self._script_config(command="module", option=option)

    def configure_local_version(self, local_version_name: str) -> None:
        """Set the LOCALVERSION option to the provided name.

        Args:
            local_version_name (str): name of the local version to configure.
        """
        self.config_set_string_option(
            option="CONFIG_LOCALVERSION",
            value=f"-{local_version_name}",
        )

    def configure_options(
        self,
        config_enables: List[Option] = (),
        config_disables: List[Option] = (),
        config_setstrings: Dict[Option, str] | None = None,
        config_modules: List[Option] = (),
    ) -> None:
        """Configure a batch of provided options.

        Args:
            config_enables (List[Option], optional):
                Configure a list of kernel options to enable. Defaults to ().
            config_disables (List[Option], optional):
                Configure a list of kernel options to disable. Defaults to ().
            config_setstrings (Dict[Option, str] | None, optional):
                Configure a set of key-value for string kernel options. Defaults to None.
            config_modules (List[Option], optional):
                Configure a list of kernel options to be built as kernel modules. Defaults to ().
        """
        for option in config_enables:
            self.config_enable_option(option=option)
        for option in config_disables:
            self.config_disable_option(option=option)
        if config_setstrings is not None:
            for option_key, option_value in config_setstrings.items():
                self.config_set_string_option(
                    option=option_key,
                    value=option_value,
                )
        for option in config_modules:
            self.config_module_option(option=option)

    def configure(
        self,
        local_version_name: str | None = None,
        original_config_pathname: PathType | None = None,
        config_enables: List[Option] = (),
        config_disables: List[Option] = (),
        config_setstrings: Dict[Option, str] | None = None,
        config_modules: List[Option] = (),
    ) -> None:
        """Execute the full configuration of the Linux build.

        Args:
            local_version_name (str | None, optional):
                name of the local version to set. If None, no local version is set.
                Defaults to None.
            original_config_pathname (PathType | None, optional):
                Path to the base configuration ("make oldconfig"). If None, no initial configuration
                is used. Defaults to None.
            config_enables (List[Option], optional):
                Configure a list of kernel options to enable. Defaults to ().
            config_disables (List[Option], optional):
                Configure a list of kernel options to disable. Defaults to ().
            config_setstrings (Dict[Option, str] | None, optional):
                Configure a set of key-value for string kernel options. Defaults to None.
            config_modules (List[Option], optional):
                Configure a list of kernel options to be built as kernel modules. Defaults to ().
        """
        self._create_initconfig(original_config_pathname=original_config_pathname)
        self._make_oldconfig()
        self._make_localmodconfig()

        self.configure_options(
            config_enables=config_enables,
            config_disables=config_disables,
            config_setstrings=config_setstrings,
            config_modules=config_modules,
        )

        if local_version_name is not None:
            self.configure_local_version(local_version_name=local_version_name)

        self.finish_config()

    def finish_config(self):
        """Conclude the configuration by running the make config one last time."""
        self._make_oldconfig()

    def apply_patch(
        self,
        patch_pathname: PathType,
        patch_level: int = 1,
    ) -> None:
        """Apply the patch from the given pathname.

        Args:
            patch_pathname (PathType): path to the patch to apply.
            patch_level (int, optional): level of patching to apply ("patch -p1"). Defaults to 1.

        Raises:
            ValueError: if patch_pathname is not a regular file.
        """
        if not os.path.isfile(patch_pathname):
            raise ValueError(
                f'Provided path file does not exist or is not a regular file: "{patch_pathname}"'
            )
        pipe_shell_out(
            command=f"patch -f -p{patch_level} < {patch_pathname}", current_dir=self._repo_path
        )

    def apply_patch_string(
        self,
        patch_string: str,
        patch_level: int = 1,
    ):
        """Apply patch from the given string (without file).

        Args:
            patch_string (str): content of the patch to apply.
            patch_level (int, optional): level of patching to apply ("patch -p1"). Defaults to 1.
        """
        shell_out(
            command=f"patch -f -p{patch_level}",
            std_input=patch_string,
            current_dir=self._repo_path,
        )

    def make(self) -> None:
        """Execute the build of the Linux kernel ("make")."""
        # TODO use benchkit target platform (also to support remote ssh target):
        nb_cpus = shell_out("nproc --all").strip()

        # TODO add support for different compilers (option CC=)

        with TimeMeasure() as make_time:
            shell_out(
                command=f"make -j {nb_cpus}",
                current_dir=self._repo_path,
                output_is_log=True,
            )

        print(f"[INFO] Linux kernel built in {make_time.duration_seconds} seconds.")

    def install(self) -> None:
        """Install the built Linux kernel ("make install")"""
        with TimeMeasure() as modules_install_time:
            shell_out(
                command="sudo make INSTALL_MOD_STRIP=1 modules_install",
                current_dir=self._repo_path,
                output_is_log=True,
            )
        with TimeMeasure() as install_time:
            shell_out(
                command="sudo make install",
                current_dir=self._repo_path,
                output_is_log=True,
            )
        print(
            "[INFO] Linux kernel modules installed "
            f"in {modules_install_time.duration_seconds} seconds."
        )
        print(f"[INFO] Linux kernel installed in {install_time.duration_seconds} seconds.")

    def get_grub_kernel_entry(
        self,
        menu_id: str,
        menu_name: str,
        isolate_all_cpus: bool,
    ) -> KernelEntry:
        """Get a grub kernel entry corresponding to this kernel build.

        Args:
            menu_id (str):
                identifier of the entry in the grub menu.
            menu_name (str):
                name of the entry in the grub menu.
            isolate_all_cpus (bool):
                whether to enable isolation of all CPUs as a boot argument.

        Returns:
            KernelEntry: the kernel entry associated to the kernel build.
        """
        kernel_version_tag = self._get_kernel_version_tag()

        result = KernelEntry(
            menu_id=menu_id,
            menu_name=menu_name,
            kernel_version=kernel_version_tag,
            disable_intel_pstate=False,
            isolate_all_cpus=isolate_all_cpus,
        )
        return result

    def install_cpupower(self) -> None:
        """Build and install `cpupower` with the sources of the current kernel."""
        kuname, dest, tools_src_dir = self._kuname_destdir_tooldir()

        shell_out(
            command="make cpupower",
            current_dir=tools_src_dir,
        )
        shell_out(
            command=f"sudo make cpupower_install DEBUG=false DESTDIR={dest}",
            current_dir=tools_src_dir,
        )

        # "fully-qualify" our custom-built cpupower (as described in '/usr/bin/cpupower')
        shell_out(
            command=f"sudo mkdir -p /usr/lib/linux-tools/{kuname}",
            current_dir=tools_src_dir,
        )
        shell_out(
            command=f"sudo ln -fs {dest}/usr/bin/cpupower /usr/lib/linux-tools/{kuname}/cpupower",
            current_dir=tools_src_dir,
        )

        os_distrib = get_distrib_id()
        if "openEuler" != os_distrib:
            # fix missing path to link to libcpupower.so
            command = f"sudo patchelf --set-rpath {dest}/usr/lib64/ {dest}/usr/bin/cpupower"
            shell_out(
                command=command,
                current_dir=tools_src_dir,
            )

    def install_perf(self) -> None:  # TODO test
        """Build and install `perf` with the sources of the current kernel."""
        _, dest_dir, tools_src_dir = self._kuname_destdir_tooldir()

        shell_out(command="make perf", current_dir=tools_src_dir)
        shell_out(command=f"sudo make perf_install DESTDIR={dest_dir}", current_dir=tools_src_dir)

    def _get_kernel_version_tag(self) -> str:
        kernel_release_path = os.path.join(self._repo_path, "include/config/kernel.release")
        with open(kernel_release_path, "r") as kernel_release_file:
            tag = kernel_release_file.read().strip()
        return tag

    def _kuname_destdir_tooldir(self) -> Tuple[str, str, str]:
        kuname = self._get_kernel_version_tag()
        dest_dir = f"/tools/{kuname}"
        shell_out(f"sudo mkdir -p {dest_dir}")
        tools_src_dir = os.path.join(self._repo_path, "tools")
        return kuname, dest_dir, tools_src_dir

    def _create_initconfig(self, original_config_pathname: PathType | None = None) -> None:
        config_path = os.path.join(self._repo_path, ".config")
        config_content = self._start_config_content(
            original_config_pathname=original_config_pathname
        )

        with open(config_path, "w") as config_file:
            config_file.write(config_content)

    def _make_oldconfig(self) -> None:
        pipe_shell_out(
            command='yes "" | make oldconfig',
            current_dir=self._repo_path,
        )

    def _make_localmodconfig(self) -> None:
        pipe_shell_out(
            command='yes "" | make localmodconfig',
            current_dir=self._repo_path,
        )

    def _script_config(
        self,
        command: str,
        option: Option,
        value: str | None = None,
    ):
        shell_command = [
            "./scripts/config",
            f"--{command}",
            f"{option}",
        ]
        if value is not None:
            shell_command.append(value)

        shell_out(command=shell_command, current_dir=self._repo_path)


def configure_cna_kernel(linux_build: LinuxBuild) -> None:
    """Example configuration of a kernel where CNA is enabled.

    Args:
        linux_build (LinuxBuild): Linux build to configure.
    """
    linux_build.configure(
        config_enables=[
            "CONFIG_NUMA_AWARE_SPINLOCKS",
        ],
        config_disables=[
            "CONFIG_DEBUG_INFO",
            "CONFIG_INTEGRITY",
            "CONFIG_MODULE_SIG",
            "CONFIG_SECURITY_LOCKDOWN_LSM",
            "SYSTEM_TRUSTED_KEYRING",
            "MODVERSIONS",
        ],
        config_setstrings={
            "CONFIG_SYSTEM_TRUSTED_KEYS": "",
            "CONFIG_SYSTEM_REVOCATION_KEYS": "",
        },
        config_modules=[
            "CONFIG_LOCK_TORTURE_TEST",
        ],
    )


def configure_standard_kernel(linux_build: LinuxBuild) -> None:
    """Example configuration of a standard kernel.

    Args:
        linux_build (LinuxBuild): Linux build to configure.
    """
    linux_build.configure(
        config_enables=[
            # For cpufreq
            "CONFIG_ACPI_CPPC_CPUFREQ_FIE",
            "CONFIG_ACPI_CPPC_LIB",
        ],
        config_disables=[
            "CONFIG_DEBUG_INFO",
            # 'CONFIG_DEBUG_INFO_DWARF5',
            "CONFIG_DEBUG_INFO_BTF",
            "CONFIG_INTEGRITY",
            "CONFIG_MODULE_SIG",
            "CONFIG_SECURITY_LOCKDOWN_LSM",
            "SYSTEM_TRUSTED_KEYRING",
            "MODVERSIONS",
        ],
        config_setstrings={
            "CONFIG_SYSTEM_TRUSTED_KEYS": "",
            "CONFIG_SYSTEM_REVOCATION_KEYS": "",
        },
        config_modules=[
            # For cpufreq
            "CONFIG_ACPI_CPPC_CPUFREQ",
            "CONFIG_SATA_AHCI_PLATFORM",
            "CONFIG_AHCI_CEVA",
            "CONFIG_AHCI_MTK",
            "CONFIG_AHCI_MVEBU",
            "CONFIG_AHCI_TEGRA",
            "CONFIG_AHCI_XGENE",
            "CONFIG_AHCI_QORIQ",
            "CONFIG_SATA_AHCI_SEATTLE",
            "CONFIG_SATA_ACARD_AHCI",
        ],
    )


def get_patch_hack_acpi_arm_cpufreq_kunpeng_bug_pathname() -> PathType:
    """Get a kernel patch file that fixes a firmware issue on Kunpeng 920.

    Returns:
        PathType: path of the patch file.
    """
    patch_pathname = os.path.join(
        parentdir(__file__),
        "patches",
        "hack_acpi_arm_cpufreq_kunpeng_bug.patch",
    )
    return patch_pathname


def patch_hack_acpi_arm_cpufreq_kunpeng_bug(linux_build: LinuxBuild) -> None:
    """Apply a kernel patch to the given Linux build that fixes a firmware issue on Kunpeng 920.

    Args:
        linux_build (LinuxBuild): Linux build to be patched.
    """
    patch_pathname = get_patch_hack_acpi_arm_cpufreq_kunpeng_bug_pathname()
    with open(patch_pathname, "r") as patch_file:
        acpi_patch = patch_file.read()
    linux_build.apply_patch_string(patch_string=acpi_patch)


def _main_cna_git():
    """Run example with CNA kernel from git repo."""
    linux_build = LinuxBuild(repo_path="/tmp/kernel.cna.git")
    configure_cna_kernel(linux_build=linux_build)
    linux_build.configure_local_version(local_version_name="cna")
    linux_build.make()
    linux_build.install()


def _main_cna_tb():
    """Run example with CNA kernel from kernel.org tarball."""
    linux_build = LinuxBuild.from_tarball(
        repo_path="/tmp/ltb/linux-6.1.8",
        tarball_dir="/tmp/ltb",
        tarball_url="https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.1.8.tar.xz",
    )
    configure_cna_kernel(linux_build=linux_build)
    linux_build.configure_local_version(local_version_name="cnatb")
    linux_build.make()
    linux_build.install()


if __name__ == "__main__":
    _main_cna_git()
    _main_cna_tb()
