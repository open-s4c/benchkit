#!/usr/bin/env python3

from benchkit.helpers.flasher.openocd import OpenOCDFlasher
import pathlib

if __name__ == "__main__":
    """
    this test requires OpenOCD to be installed on host and, to have a device
    connected that is supported by OpenOCD and the specified board configuration
    (e.g., "st_nucleo_l4")
    """
    device: str = "st_nucleo_l4"
    openocd = OpenOCDFlasher.with_board(board=device, need_sudo=True)

    # to flash an a file do : 
    # openocd.flash(bin=pathlib.Path("firmware.elf").resolve(), addr="0x08000000")

    openocd.stop()
    openocd.start()
    openocd.reset()
