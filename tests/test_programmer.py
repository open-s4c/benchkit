#!/usr/bin/env python3

from benchkit.helpers.programmer.openocd import OpenOCDProgrammer  

if __name__ == "__main__":
    openocd = OpenOCDProgrammer(interface="stlink", target="stm32l4x")
    openocd.reset()
