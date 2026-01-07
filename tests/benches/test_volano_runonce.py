# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
import subprocess
import time
from pathlib import Path

from benchkit.benches.volano import VolanoBench
from benchkit.core.benchmark import Benchmark
from benchkit.core.bktypes.contexts import FetchContext
from benchkit.engine.runonce import run_once
from benchkit.utils.logging import bkpprint, bkprint, configure_logging


def main() -> None:
    configure_logging(
        rich=True,
        level=logging.DEBUG,
        stdout_level=logging.INFO,
        file_level=logging.DEBUG,
    )

    bench: Benchmark = VolanoBench()

    benchkit_home_dir = Path("~/.benchkit/").expanduser().resolve()
    benches_dir = benchkit_home_dir / "benches"
    results_dir = benchkit_home_dir / "results"

    fc = FetchContext.from_args(
        fetch_args={
            "parent_dir": benches_dir,
        }
    )
    bench.fetch(ctx=fc, **fc.fetch_args)

    command = "./startup.sh server loop openjdk"

    process = subprocess.Popen(
        command,
        shell=True,
        cwd=benches_dir / "volano",
    )

    time.sleep(5)

    result = run_once(
        bench=VolanoBench(),
        args={
            "parent_dir": benches_dir,
            "start": 1,
            "rooms": 50,
            "users": 20,
            "count": 101,
            "pause": 0,
            "host": "localhost",
        },
        duration_s=2,
        record_dir=results_dir,
    )

    bkprint("Benchmark result:")
    bkpprint(result)

    process.terminate()


if __name__ == "__main__":
    main()
