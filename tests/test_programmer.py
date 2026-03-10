#!/usr/bin/env python3

from benchkit.helpers.programmer.openocd import OpenOCDProgrammer  
import pathlib

if __name__ == "__main__":
    openocd = OpenOCDProgrammer.with_board(board="st_nucleo_l4", need_sudo=True)
    # openocd.flash(bin=pathlib.Path("blink.elf").resolve(), addr="0x08000000")
    #openocd.stop()
    openocd.start()
    # openocd.reset()
