# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from . import Programmer

from benchkit.platforms import Platform, get_current_platform
from benchkit.helpers.linux.groups import current_user_in_group

import pathlib

class OpenOCDProgrammer(Programmer):
    def __init__(
            self,
            interface: str,
            target: str,
            need_sudo: bool = True,
    ) -> None:
        """
        Args:
            interface: openocd interface to use (e.g., "stlink")
            target: The OpenOCD target to use (e.g., "stm32l4x").
            need_sudo: Whether to use sudo when invoking OpenOCD. 
        """
        self._interface: str | None = f"interface/{interface}.cfg"
        self._target: str | None = f"target/{target}.cfg"
        self._board: str | None = None
        self.__need_sudo: bool = need_sudo

    @staticmethod
    def with_board(
            board: str,
            need_sudo: bool = True,
    ) -> "OpenOCDProgrammer":
        """
        Configure the programmer for a specific board. This is a no-op for OpenOCD since the interface and target are already specified.
        Args:
            board: The name of the board (e.g., "st_nucleo_l4")
            need_sudo: Whether to use sudo when invoking OpenOCD
        Returns:
            An instance of OpenOCDProgrammer configured for the specified board.
        """
        s = OpenOCDProgrammer(
            interface = None,
            target = None,
            need_sudo=need_sudo,
        )

        s._board: str | None = f"board/{board}.cfg"
        return s

    @property
    def __cmd_prefix(self) -> str:
        """
        Get the command prefix for invoking OpenOCD, optionally with sudo.
        """
        return (
            f"{'sudo' if self.__need_sudo else ''} openocd -f {self._interface} -f {self._target}"
        ) if self._board is None else (
            f"{'sudo' if self.__need_sudo else ''} openocd -f {self._board}"
        )


    def flash(
            self,
            bin: pathlib.Path,
            addr: str,
    ) -> None:
        """
        Flash the firmware onto the board via OpenOCD.
        Args:
            bin: The path to the binary to flash.
            addr: The address to flash the binary to (e.g., "0x08000000").
        
        HACK addr is str because we use the hex format and don't want decimal
        """
        plat: Platform = get_current_platform()

        plat.comm.shell(
            command=self.__cmd_prefix.split(" ") + [
                "-c",
                f"program {bin} {addr} reset exit"
            ],
            print_output=False,
        )

    def reset(self) -> None:
        """
        Reset the board via OpenOCD.
        """
        plat: Platform = get_current_platform()
        plat.comm.shell(
            command=(
                f"{self.__cmd_prefix} "
                '-c "init" '
                '-c "reset" '
                '-c "exit"'
            ),
            print_output=False,
            print_input=True,
        )


    def start(self) -> None:
        """
        Start the device (e.g., by running it or exiting reset).
        """
        plat: Platform = get_current_platform()
        plat.comm.shell(
            command=self.__cmd_prefix.split(" ") + [
                '-c', 'init',
                '-c', 'reset run',
                '-c', 'exit',
            ],
            print_output=False,
            print_input=True,
        )

    def stop(self) -> None:
        """
        Stop the device (e.g., by halting it or entering reset).
        """
        plat: Platform = get_current_platform()
        plat.comm.shell(
            command=self.__cmd_prefix.split(" ") + [
                '-c', 'init',
                '-c', 'reset halt',
                '-c', 'exit',
            ],
            print_output=False,
            print_input=True,
        )
