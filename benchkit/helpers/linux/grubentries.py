# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Smooth management of the grub menu.
This module provides the ability to add kernel entries to the grub menu and change the default
kernel entry.
"""

import collections
import os
import os.path
import re
from typing import List, Tuple

from benchkit.communication import CommunicationLayer, LocalCommLayer
from benchkit.shell.shell import shell_out
from benchkit.utils.types import PathType


def _get_nb_cpus():
    cmd_output = shell_out("nproc --all")
    result = int(cmd_output.strip())
    return result


def get_existing_menu_entries(grub_generated_config_path: PathType) -> List[Tuple[str, str]]:
    """Return all the existing kernel entries in Grub menu.

    Args:
        grub_generated_config_path (PathType):
            path to the Grub generation configuration file.

    Returns:
        List[Tuple[str, str]]:
            a list of entries represented as tuples, where the first element of the tuple is the
            pretty identifier of the entry and the second is the keys of the entry.
    """
    with open(grub_generated_config_path, "r") as grub_cfg_file:
        grub_cfg_file_content = grub_cfg_file.readlines()

    grub_cfg_file_iter = iter(grub_cfg_file_content)

    entries = []
    for raw_line in grub_cfg_file_iter:
        if raw_line.lstrip().startswith("menuentry "):
            line = raw_line.strip()
            m = re.match(
                pattern=r"menuentry '(.*)'.*menuentry_id_option '(.*)'",
                string=line,
            )
            pretty, keys = m.groups()
            entries.append((pretty, keys))

    return entries


def _get_original_config_block(grub_generated_config_path, kernel_version):
    with open(grub_generated_config_path, "r") as grub_cfg_file:
        grub_cfg_file_content = grub_cfg_file.readlines()

    grub_cfg_file_iter = iter(grub_cfg_file_content)

    found = False
    lines = []
    for line in grub_cfg_file_iter:
        if line.lstrip().startswith("menuentry "):
            if kernel_version in line:
                found = True
                lines.append(line.rstrip())
                break
    if found:
        for line in grub_cfg_file_iter:
            lines.append(line.rstrip())
            if line.lstrip().startswith("}"):
                break
        return "\n".join(lines)

    # Entry with corresponding kernel not found, fallback to main entry
    grub_cfg_file_iter = iter(grub_cfg_file_content)
    found = False
    lines = []
    for line in grub_cfg_file_iter:
        if line.startswith("menuentry 'Ubuntu'"):
            found = True
            lines.append(line.rstrip())
            break
    if not found:
        raise ValueError(
            (
                f"Impossible to find main kernel configuration "
                f"in Grub file: {grub_generated_config_path}"
            )
        )
    for line in grub_cfg_file_iter:
        lines.append(line.rstrip())
        if line.lstrip().startswith("}"):
            break
    return "\n".join(lines)


def _plug_menu_id(
    config_block,
    menu_id,
):
    new_config_block = str(config_block)
    new_config_block = re.sub(
        pattern=r"menuentry_id_option '.+' {",
        repl=f"menuentry_id_option '{menu_id}' {{",
        string=new_config_block,
    )
    return new_config_block


def _plug_menu_name(
    config_block,
    menu_name,
):
    new_config_block = str(config_block)
    new_config_block = re.sub(
        pattern=r"menuentry '.+' --class",
        repl=f"menuentry '{menu_name}' --class",
        string=new_config_block,
    )
    return new_config_block


def _plug_kernel(
    config_block,
    kernel_version,
):
    new_config_block = str(config_block)
    new_config_block = re.sub(
        pattern=r"/boot/vmlinuz-\S*\s",
        repl=f"/boot/vmlinuz-{kernel_version} ",
        string=new_config_block,
    )
    new_config_block = re.sub(
        pattern=r"/boot/initrd.img-\S*\n",
        repl=f"/boot/initrd.img-{kernel_version}\n",
        string=new_config_block,
    )
    return new_config_block


def _indent_correctly(config_block):
    if config_block.startswith("\t"):
        new_config_block = str(config_block).splitlines()
        for i, line in enumerate(new_config_block):
            if line.startswith("\t"):
                new_config_block[i] = line[1:]
        return "\n".join(new_config_block)

    return config_block


def _add_args(config_block, args):
    config_block_lst = config_block.split("\n")
    for i, line in enumerate(config_block_lst):
        if line.strip().startswith("linux"):
            config_block_lst[i] += " " + args
    return "\n".join(config_block_lst)


class KernelEntry:
    """Represent a boot kernel entry in Grub menu."""

    def __init__(
        self,
        menu_id: str,
        menu_name: str,
        kernel_version: str,
        disable_intel_pstate: bool = False,
        isolate_all_cpus: bool = False,
        additional_bootargs: str = "",
    ):
        self._menu_id = menu_id
        self._menu_name = menu_name
        self._kernel_version = kernel_version
        self._disable_intel_pstate = disable_intel_pstate
        self._isolate_all_cpus = isolate_all_cpus
        self._additional_bootargs = additional_bootargs

    @property
    def menu_id(self) -> str:
        """Get the identifier of the kernel entry in the Grub meny.

        Returns:
            str: the identifier of the kernel entry in the Grub meny.
        """
        return self._menu_id

    @property
    def kernel_version(self) -> str:
        """Get the kernel version used in this kernel entry.

        Returns:
            str: the kernel version used in this kernel entry.
        """
        return self._kernel_version

    def get_config_block(self, grub_generated_config_path: str) -> str:
        """Generate the configuration block for this kernel entry for the Grub configuration file.

        Args:
            grub_generated_config_path (str): path to the generated configuration file of Grub.

        Returns:
            str: the configuration block of this kernel entry, mimicking the structure of the
            configuration already present in the generated configuration file.
        """
        config_block = _get_original_config_block(
            grub_generated_config_path=grub_generated_config_path,
            kernel_version=self._kernel_version,
        )
        config_block = _plug_menu_id(config_block=config_block, menu_id=self.menu_id)
        config_block = _plug_menu_name(config_block=config_block, menu_name=self._menu_name)
        config_block = _plug_kernel(config_block=config_block, kernel_version=self._kernel_version)
        config_block = _indent_correctly(config_block=config_block)

        boot_args = self._generate_boot_args()
        config_block = _add_args(config_block=config_block, args=boot_args)
        return config_block

    def _generate_boot_args(self):
        args = []
        if self._disable_intel_pstate:
            args.append("intel_pstate=disable")
        if self._isolate_all_cpus:
            cpuid_max = _get_nb_cpus() - 1
            args.append(f"isolcpus=1-{cpuid_max}")
        args.append(self._additional_bootargs)
        result = " ".join(args)
        return result


def _generate_kernel_entries_file(
    kernel_entries: List[KernelEntry],
    grub_generated_config_path: PathType,
    grub_entries_config_head_path: PathType,
    grub_entries_added_config_path: PathType,
    force_write: bool,
    comm_layer: CommunicationLayer,
):
    if not force_write and os.path.exists(grub_entries_added_config_path):
        raise ValueError(
            f'File "{grub_entries_added_config_path}" exists, please remove it or rename it first.'
        )

    with open(grub_entries_config_head_path, "r") as file:
        head = file.readlines()[:2]
    menu_entries = [
        ke.get_config_block(grub_generated_config_path=grub_generated_config_path)
        for ke in kernel_entries
    ]

    body = "\n\n".join(menu_entries)
    content = "".join(head) + "\n" + body

    print(f"Writing Grub menu entries (to {grub_entries_added_config_path}).")
    comm_layer.write_content_to_file(
        content=content,
        output_filename=grub_entries_added_config_path,
        privileged=True,
    )

    print(f"Modifying permissions (of {grub_entries_added_config_path}).")
    shell_out(f"sudo chmod 755 {grub_entries_added_config_path}")


def _replace_match(
    content: str,
    match: re.Match,
    callback=lambda body: body,
):
    start = match.start()
    end = match.end()
    head = content[:start]
    body = content[start:end]
    tail = content[end:]

    new_body = callback(body)
    new_content = head + new_body + tail
    return new_content


def _comment_match(content, match):
    def add_leading_dash(body):
        return f"\n#{body[1:]}"

    return _replace_match(content, match, add_leading_dash)


def _appendleft_match(content, match, new_content):
    def append_left(body):
        return f"{new_content}{body}"

    return _replace_match(content, match, append_left)


def _match_is(expected, match):
    gd = match.groupdict()
    actual = gd["value"]
    return expected == actual


def set_grub_default(
    default_id: str,
    grub_config_path: PathType = "/etc/default/grub",
    comm_layer: CommunicationLayer = LocalCommLayer(),
):
    """Set the default kernel entry in Grub menu to be the given one.

    Args:
        default_id (str):
            identifier of the kernel entry to set as default.
        grub_config_path (PathType, optional):
            Path to grub configuration file (not the generated one).
            Defaults to "/etc/default/grub".
        comm_layer (CommunicationLayer, optional):
            Communication layer of the target host to set the default entry.
            Defaults to LocalCommLayer().
    """
    grub_config_path_bak = grub_config_path + ".bak"

    original_file_content = comm_layer.read_file(path=grub_config_path)

    config_touched = False
    file_content = str(original_file_content)
    while (
        (m := re.search(pattern=r"\nGRUB_DEFAULT=(?P<value>.*)\n", string=file_content)) is not None
    ) and not _match_is(default_id, m):
        body = file_content[m.start() : m.end()]
        current_id = body.strip().split("=")[-1]
        if current_id != default_id:
            config_touched = True
            file_content = _comment_match(content=file_content, match=m)

    if config_touched:
        m = re.search(pattern=r"\n#GRUB_DEFAULT=.*\n", string=file_content)
        file_content = _appendleft_match(
            content=file_content,
            match=m,
            new_content=f"\nGRUB_DEFAULT={default_id}",
        )

    if config_touched:
        print(f"Saving grub config backup (to {grub_config_path_bak}).")
        if not comm_layer.path_exists(grub_config_path_bak):
            comm_layer.write_content_to_file(
                content=original_file_content,
                output_filename=grub_config_path_bak,
                privileged=True,
            )

        print(f"Modifying GRUB_DEFAULT in default grub config (writing to {grub_config_path}).")
        comm_layer.write_content_to_file(
            content=file_content,
            output_filename=grub_config_path,
            privileged=True,
        )


def interactive_set_grub_default(
    grub_generated_config_path: PathType,
    grub_config_path: PathType,
) -> None:
    """Provides an interactive menu to set the default entry in the Grub menu.

    Args:
        grub_generated_config_path (PathType):
            path to generated grub configuration file.
        grub_config_path (PathType):
            path to grub configuration file (not the generated one).
    """
    entries = get_existing_menu_entries(grub_generated_config_path=grub_generated_config_path)
    biggest_pretty = max(len(entry[0]) for entry in entries) + 4
    biggest_key = max(len(entry[1]) for entry in entries) + 4
    done = False

    while not done:
        print(
            "Please enter the id number (first column) of the kernel "
            "you want to configure as default booting one:"
        )
        print(f"{0: >4}  -- Exit program without change --")
        for i, (pretty, key) in enumerate(entries, start=1):
            print(f"{i: >4}  {pretty: <{biggest_pretty}}{key: <{biggest_key}}")
        print()
        print("> ", end="")

        choice = input()

        if choice.isdigit():
            int_choice = int(choice)
            if 0 == int_choice:
                done = True
            elif int_choice > len(entries):
                pass
            else:
                pretty, key = entries[int_choice - 1]

                print(f"Chosen kernel entry: '{pretty}'")
                print(f"Chosen kernel key: '{key}'")

                print("Applying choice.")

                set_grub_default(default_id=key, grub_config_path=grub_config_path)
                shell_out("sudo update-grub")
                done = True


def add_kernel_entries_to_grub(
    kernel_entries: List[KernelEntry],
    default_entry: int,
    grub_config_path: PathType,
    grub_generated_config_path: PathType,
    grub_entries_config_head_path: PathType,
    grub_entries_added_config_path: PathType,
    force_write: bool,
    comm_layer: CommunicationLayer = LocalCommLayer(),
) -> None:
    """Add boot kernel entries to grub menu.

    Args:
        kernel_entries (List[KernelEntry]):
            list of kernel entries to add.
        default_entry (int):
            index in kernel_entries of the default entry to set.
        grub_config_path (PathType):
            path of the grub configuration file (not generated).
        grub_generated_config_path (PathType):
            path of the generated grub configuration file.
        grub_entries_config_head_path (PathType):
            TODO
        grub_entries_added_config_path (PathType):
            path where to write the configuration of the newly added kernel entries.
        force_write (bool):
            whether to force the write of grub_entries_added_config_path if the file already exists.
        comm_layer (CommunicationLayer, optional):
            Communication layer to reach the host where to add the kernel entries.
            Defaults to LocalCommLayer().

    Raises:
        ValueError: if there are duplicated identifiers in the list of kernel entries.
    """
    # Check if there is no duplicate within the specified menu identifiers.
    id_counter = collections.Counter([ke.menu_id for ke in kernel_entries])
    id_duplicates = [ke for ke in id_counter if id_counter[ke] > 1]
    if id_duplicates:
        id_duplicates_str = " ".join(id_duplicates)
        s = "s" if len(id_duplicates) > 1 else ""
        raise ValueError(f"Duplicate{s} menu identifier{s}: {id_duplicates_str}.")

    _generate_kernel_entries_file(
        kernel_entries=kernel_entries,
        grub_generated_config_path=grub_generated_config_path,
        grub_entries_config_head_path=grub_entries_config_head_path,
        grub_entries_added_config_path=grub_entries_added_config_path,
        force_write=force_write,
        comm_layer=comm_layer,
    )

    default_entry_id = kernel_entries[default_entry].menu_id
    set_grub_default(default_id=default_entry_id, grub_config_path=grub_config_path)

    print("Changes to Grub configuration done. Do not forget to run:\n  update-grub")


def find_last_vanilla() -> str:
    """Finds the last vanilla version of Ubuntu kernel on the current system.

    Raises:
        ValueError: If no generic kernel can be found in /boot

    Returns:
        str: the last vanilla version of Ubuntu kernel on the current system.
    """
    prefix = "vmlinuz-"
    listed_files = sorted(
        [f for f in os.listdir("/boot") if f.startswith(prefix) and f.endswith("-generic")],
        reverse=True,
    )
    if len(listed_files) == 0:
        raise ValueError("No *-generic kernel found in /boot")
    result = listed_files[0][len(prefix) :]
    return result


def vanilla_kernel_entry() -> KernelEntry:
    """Get the kernel entry corresponding to the vanilla kernel of the Grub menu.
    The vanilla kernel entry is the unmodified kernel as originally packaged in the distribution.

    Returns:
        KernelEntry: the vanilla kernel entry from the Grub menu.
    """

    def shorten(tag: str) -> str:
        result = tag.replace(".", "").replace("-", "")
        return result

    vanilla_kernel_version = find_last_vanilla()
    short_vanilla = shorten(vanilla_kernel_version)

    return KernelEntry(
        menu_id=f"ubuntu_{short_vanilla[:6]}_vanilla",
        menu_name=f"Vanilla Ubuntu {vanilla_kernel_version}, normal boot",
        kernel_version=vanilla_kernel_version,
        disable_intel_pstate=False,
        isolate_all_cpus=False,
    )


def _get_arch() -> str:
    raw_output = shell_out("uname -m")
    arch = raw_output.strip()
    return arch


def arch_is_x86_64() -> bool:
    """Return whether the architecture of the local host is x86_64.

    Returns:
        _type_: whether the architecture of the local host is x86_64.
    """
    return "x86_64" == _get_arch()
