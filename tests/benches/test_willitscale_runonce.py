# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.benches.willitscale import WillitscaleBench
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
        bench=WillitscaleBench(),
        args={
            "parent_dir": benches_dir,
            "commit": "a34a85cc1e9b9b74e94fdd3ecc479019da610e6a",
            "patches": [
                Path("../../examples/willitscale/patch.diff").resolve(),
            ],
            "test_name": "lock1_processes",
            "nb_warmup_iterations": 1,
            "nb_threads": 3,
        },
        duration_s=2,
        record_dir=results_dir,
    )

    bkprint("Benchmark result:")
    bkpprint(result)


if __name__ == "__main__":
    main()
