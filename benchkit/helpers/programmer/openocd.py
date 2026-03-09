# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from . import Programmer

from benchkit.platforms import Platform, get_current_platform
from benchkit.helpers.linux.groups import current_user_in_group

class OpenOCDProgrammer(Programmer):
    def __init__(self, interface: str, target: str) -> None:
        self._interface: str = f"interface/{interface}.cfg"
        self._target: str = f"target/{target}.cfg"

    def __cmd_prefix(self, sudo: bool) -> str:
        """
        Get the command prefix for invoking OpenOCD, optionally with sudo.
        """
        return (
            f"{'sudo' if sudo else ''} openocd -f {self._interface} -f {self._target}"
        )

    def __need_sudo(self) -> bool:
        """
        Check if the current user needs sudo to access the programmer.
        """
        return not all(current_user_in_group(g) for g in ["dialout", "plugdev"])

    def flash(self, bin: pathlib.Path, addr: str) -> None:
        """
        HACK addr is str because we use the hex format and don't want decimal
        """
        plat: Platform = get_current_platform()
        plat.comm.shell(
            command=[
                "sudo",
                "openocd",
                "-f",
                self._interface,
                "-f",
                self._target,
                "-c",
                f"program {bin} {addr} verify reset exit",
            ],
            print_output=False,
        )

    def reset(self) -> None:
        plat: Platform = get_current_platform()
        plat.comm.shell(
            command=(
                f"{self.__cmd_prefix(sudo=self.__need_sudo())} "
                '-c "init" '
                '-c "reset" '
                '-c "exit"'
            ),
            print_output=False,
        )
