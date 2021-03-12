# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities regarding Linux distributions.
"""

import csv
from typing import Dict


def _get_os_release_info() -> Dict[str, str]:
    config_pathname = "/etc/os-release"

    with open(config_pathname, "r") as config_file:
        reader = csv.reader(config_file, delimiter="=")
        os_release = {e[0]: e[1] for e in reader if len(e) > 1}

    return os_release


def get_distrib_id() -> str:
    """Get the identifier of the distribution running currently on the local host.

    Returns:
        str: the identifier of the distribution running currently on the local host.
    """
    os_release = _get_os_release_info()
    return os_release["ID"]
