# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
import time
from pathlib import Path

from benchkit.benches.volano import VolanoBench
from benchkit.core.benchmark import Benchmark
from benchkit.core.bktypes.contexts import FetchContext
from benchkit.engine.runonce import run_once
from benchkit.shell.shellasync import shell_async
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

    # Explicityly call the fetch of the benchmark to make sure the ./startup.sh script is present.
    fc = FetchContext.from_args(
        fetch_args={
            "parent_dir": benches_dir,
        }
    )
    bench.fetch(ctx=fc, **fc.fetch_args)

    # Startup the chat server and wait for 5 seconds such that it had the time to startup.
    command = "./startup.sh server loop openjdk"

    process = shell_async(
        command=command,
        stdout_path=results_dir / "volano_server.out",
        stderr_path=results_dir / "volano_server.err",
        platform=fc.platform,
        current_dir=benches_dir / "volano",
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

    # Kill the chatserver after the benchmark is done.
    if process is not None:
        exitcode = process.premature_exitcode()

        is_running = exitcode is None
        exited_with_error = exitcode not in (None, 0)

        if exited_with_error:
            raise ValueError(
                f"Volano Server exited prematurely with code {exitcode}, please check logs\n"
            )

        if is_running:
            process.stop()


if __name__ == "__main__":
    main()
