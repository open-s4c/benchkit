# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
RunOnce engine for benchkit.

This engine runs one benchmark pipeline end-to-end:
fetch (optional) -> build (optional) -> run (required) -> collect (optional)

The engine:
- validates the benchmark shape
- constructs contexts
- skips missing steps
- delegates step execution to an Executor
"""

import json
from dataclasses import dataclass
from pathlib import Path

from benchkit.core.benchmark import Benchmark
from benchkit.core.bktypes import RecordResult, Vars
from benchkit.core.validatebench import validate_benchmark
from benchkit.engine.executor import LocalExecutor
from benchkit.engine.stepper import Stepper
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import get_results_dir
from benchkit.utils.logging import get_logger


@dataclass(frozen=True)
class RunOnceEngine:
    """
    Engine that runs a benchmark exactly once.

    Notes:
    - run() must exist.
    - fetch/build/collect are optional.
    - If fetch is missing, you must provide fetch_result explicitly or the
      benchmark must not need it (build/run must not rely on ctx.fetch_result).
    - Similarly for build.
    """

    executor = LocalExecutor()

    def run_once(
        self,
        *,
        bench: Benchmark,
        args: Vars,
        duration_s: int | None = None,
        record_dir: Path | None = None,
    ) -> RecordResult:
        log = get_logger("engine.runonce")
        validate_benchmark(bench=bench)
        record_dir = get_results_dir(results_dir=record_dir)

        platform = get_current_platform()

        log.debug("Starting benchmark.")
        stepper = Stepper(bench=bench, platform=platform)
        log.debug("Fetching...")
        session = stepper.fetch(args=args, record_dir=record_dir)
        log.debug("Building...")
        session = stepper.build(session=session, args=args)
        log.debug("Running...")
        session = stepper.run(session=session, args=args, duration_s=duration_s)
        log.debug("Collecting...")
        session = stepper.collect(session=session, args=args)
        log.debug("Benchmark completed.")
        result = session.record_result

        output_dict = {
            "benchmark": bench.__class__.__name__,
            "args": {str(k): str(v) for k, v in args.items()},
            "used_defaults": {str(k): str(v) for k, v in session.collect_ctx.default_args.items()},
            "results": result,
        }

        if record_dir is not None:
            if not record_dir.is_dir():
                log.info(f"Creating record directory {record_dir}")
                record_dir.mkdir(parents=True, exist_ok=True)
            json_result_path = record_dir / "result.json"
            json_result_path.write_text(json.dumps(output_dict, indent=2))
            log.info(f"Result saved to {json_result_path}")

        return result


def run_once(
    *,
    bench: Benchmark,
    args: Vars,
    duration_s: int | None = None,
    record_dir: Path | None = None,
) -> RecordResult:
    engine = RunOnceEngine()
    result = engine.run_once(
        bench=bench,
        args=args,
        duration_s=duration_s,
        record_dir=record_dir,
    )
    return result
