#!/usr/bin/env python3
# Copyright (C) 2024 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to test the HDC api basics
"""


import os

from benchkit.hdc import OpenHarmonyDeviceConnector

HOST_FILE = ".gitignore"
TMP_FILE = "cloned-gitignore"
TARGET_FILE = "/storage/media/100/local/testing/.gitignore"


def main() -> None:
    device = OpenHarmonyDeviceConnector.query_devices(lambda _: True)[0]
    print(device)

    bridge = OpenHarmonyDeviceConnector(device)
    output = bridge._target_shell_out("cd data && ls")
    print(output)

    bridge.push(HOST_FILE, TARGET_FILE)
    bridge.pull(TARGET_FILE, TMP_FILE)

    f = open(TMP_FILE, "r")
    content = f.read()
    print(content)
    f.close()

    os.remove(f.name)


if __name__ == "__main__":
    main()
