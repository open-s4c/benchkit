# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to emulate tee behavor.
"""

from typing import TextIO


def teeprint(content: str, file: TextIO):
    """
    Prints content to both stdout and given file.

    Args:
        content (str): content to append to the given file.
        file (TextIO): given file to append to.
    """
    print(content, file=file)
    print(content)
    file.flush()
