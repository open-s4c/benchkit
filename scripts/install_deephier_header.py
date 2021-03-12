#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""Install the deep memory hierarchy header configured for the current platform.

Usage:
    install_deephier_header.py
"""

import sys

# pylint: disable=import-error
from deephierarchy import install_from_benchkit_current_platform


def main():
    """Main function of the install script."""
    header_lib = install_from_benchkit_current_platform()

    print()
    if header_lib.is_installed():
        print("Deep hierarchy installed successfully.")
    else:
        print("Error: not installed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
