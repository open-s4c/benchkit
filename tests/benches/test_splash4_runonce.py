# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.benches.splash4 import Splash4Bench
from benchkit.engine.runonce import run_once
from benchkit.utils.logging import bkpprint, bkprint, configure_logging


def main() -> None:
    configure_logging(
        rich=True,
        level=logging.DEBUG,
        stdout_level=logging.INFO,
        file_level=logging.DEBUG,
    )

    benchkit_home_dir = Path("~/.benchkit/").expanduser().resolve()
    benches_dir = benchkit_home_dir / "benches"
    results_dir = benchkit_home_dir / "results"

    result = run_once(
        bench=Splash4Bench(),
        args={
            "parent_dir": benches_dir,
            "benchmark": "fft",
            "nb_threads": 4,
        },
        duration_s=2,  # unused by SPLASH-4 (fixed-work), kept for the run_once API
        record_dir=results_dir,
    )

    bkprint("Benchmark result:")
    bkpprint(result)


if __name__ == "__main__":
    main()
