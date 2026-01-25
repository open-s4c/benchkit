# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging

from benchkit.benches.small.sleep import SleepBench
from benchkit.engine.runonce import run_once
from benchkit.utils.logging import bkpprint, bkprint, configure_logging


def main() -> None:
    configure_logging(
        rich=True,
        level=logging.DEBUG,
        stdout_level=logging.INFO,
        file_level=logging.DEBUG,
    )

    result = run_once(
        bench=SleepBench(),
        args={
            "duration_seconds": "1",
        },
    )

    bkprint("Benchmark result:")
    bkpprint(result)


if __name__ == "__main__":
    main()
