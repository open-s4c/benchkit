# Copyright (C) 2024 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to test the ADB and HDC comm layer API.
"""
from enum import Enum

from benchkit.platforms import Platform, get_current_platform


class Target(Enum):
    LOCAL = 1
    HARMONY = 2
    ANDROID = 3


def main() -> None:
    target = Target.ANDROID
    current_dir = "./"

    match target:
        case Target.LOCAL:
            platform = get_current_platform()
            print(platform)
        case Target.HARMONY:
            from benchkit.devices.hdc import OpenHarmonyCommLayer, OpenHarmonyDeviceConnector

            device = list(OpenHarmonyDeviceConnector.query_devices())[0]
            hdc = OpenHarmonyDeviceConnector.from_device(device)
            comm = OpenHarmonyCommLayer(hdc)
            print(device)
            platform = Platform(comm)
        case Target.ANDROID:
            from benchkit.devices.adb import AndroidCommLayer, AndroidDebugBridge

            device = list(AndroidDebugBridge.query_devices())[0]
            adb = AndroidDebugBridge.from_device(device)
            comm = AndroidCommLayer(adb)
            print(comm)
            platform = Platform(comm)
        case _:
            platform = get_current_platform()

    output = platform.comm.shell(
        command="ls",
        current_dir=current_dir,
        environment={},
        output_is_log=False,
    )

    print(output)


if __name__ == "__main__":
    main()
