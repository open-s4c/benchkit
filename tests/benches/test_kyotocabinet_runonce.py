# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.benches.kyotocabinet import KyotoCabinetBench
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
        bench=KyotoCabinetBench(),
        args={
            "parent_dir": benches_dir,
            "patches": [
                Path("../../examples/kyotocabinet/patches/01-cloudflare.diff").resolve(),
                Path("../../examples/kyotocabinet/patches/02-cloudflare.diff").resolve(),
                Path("../../examples/kyotocabinet/patches/03-benchmark.diff").resolve(),
                Path("../../examples/kyotocabinet/patches/04-benchkit.diff").resolve(),
            ],
            "nb_threads": 3,
        },
        duration_s=2,
        record_dir=results_dir,
    )

    bkprint("Benchmark result:")
    bkpprint(result)


if __name__ == "__main__":
    main()
