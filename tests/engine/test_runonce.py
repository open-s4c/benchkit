# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.benches.rocksdb import RocksDBBench
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
        bench=RocksDBBench(),
        args={
            "parent_dir": benches_dir,
            "commit": "v10.7.5",
            "bench_name": "readrandom",
            "nb_threads": 3,
        },
        duration_s=2,
        record_dir=results_dir,
    )

    bkprint("Benchmark result:")
    bkpprint(result)


if __name__ == "__main__":
    main()
