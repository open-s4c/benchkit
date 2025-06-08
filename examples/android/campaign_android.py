#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pythainer.examples.builders import get_user_builder


def docker():
    builder = get_user_builder(
        image_name="bkandroidsdk",
        base_ubuntu_image="ubuntu:22.04",
    )
    builder.root()
    builder.add_packages(packages=["unzip", "wget", "build-essential"])
    builder.user()
    builder.run_multiple(
        commands=[
            "mkdir /home/${USER_NAME}/workspace/libraries",
            "cd...",
            "wget https://dl.google.com/android/repository/android-sdk-linux-tools_r33b+3-linux.zip",
            "unzip android-sdk-linux-tools_r33b+3-linux.zip",
            "mv android-sdk-linux /usr/local/android-sdk",
            "export PATH=/usr/local/android-sdk/tools:$PATH",
        ],
    )
    builder.build()


def main() -> None:
    docker()


if __name__ == "__main__":
    main()
