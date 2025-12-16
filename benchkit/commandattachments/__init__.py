# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import time
from typing import List

from benchkit.platforms.generic import Platform
from benchkit.utils.types import PathType


def wait_for_output(
    output_files: List[PathType], platform: Platform, max_wait_s: int = 5, poll_rate_rate: int = 20
) -> None:
    max_iterations = max_wait_s * poll_rate_rate

    for _ in range(max_iterations):
        if any((platform.comm.file_size(file) > 0) for file in output_files):
            break
        time.sleep(1 / poll_rate_rate)
    else:
        raise TimeoutError("Attachment was not able to attach")
