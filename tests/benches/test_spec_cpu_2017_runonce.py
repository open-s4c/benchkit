# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
import sys
from pathlib import Path

from benchkit.benches.speccpu2017 import SPECCPU2017Bench
from benchkit.engine.runonce import run_once
from benchkit.utils.logging import bkpprint, bkprint, configure_logging


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python test_spec_cpu_2017_runonce.py <PATH_TO_SPEC_ISO>", file=sys.stderr)
        exit(1)

    spec_source = Path(sys.argv[1]).expanduser().resolve()

    if not spec_source.is_file():
        print(f"SPEC ISO file not found: {spec_source}", file=sys.stderr)
        exit(1)

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
        bench=SPECCPU2017Bench(),
        args={
            "parent_dir": benches_dir,
            "spec_source_iso": spec_source,
            "bench_name": "500.perlbench",
            "size": "test",
        },
        record_dir=results_dir,
    )

    bkprint("Benchmark result:")
    bkpprint(result)


if __name__ == "__main__":
    main()
