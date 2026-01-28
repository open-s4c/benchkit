# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.benches.speccpu2017 import SPECCPU2017Bench
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
    spec_source = Path("PATH_TO_SPEC_ISO").expanduser().resolve()

    result = run_once(
        bench=SPECCPU2017Bench(),
        args={
            "parent_dir": benches_dir,
            "spec_source_iso": spec_source / "cpu2017-1.1.9.iso",
            "bench_name": "500.perlbench",
            "size": "test",
        },
        record_dir=results_dir,
    )

    bkprint("Benchmark result:")
    bkpprint(result)


if __name__ == "__main__":
    main()
