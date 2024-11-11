#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Module to test the ADB api basics
"""

from benchkit.adb import ADBDevice, AndroidCommLayer, AndroidDebugBridge
from benchkit.platforms.generic import Platform

def main() -> None:
    devices = list(AndroidDebugBridge._devices())
    device: ADBDevice
    if devices:
        device = devices[0]
    else:
        exit("No device found")

    bridge = AndroidDebugBridge.from_device(device)

    comm = AndroidCommLayer(bridge)
    platform = Platform(comm_layer=comm)

    output = platform.comm.shell(command="ls")
    print(output)


if __name__ == "__main__":
    main()
