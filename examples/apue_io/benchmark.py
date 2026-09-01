# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit benchmark for the APUE Figure 3.6 I/O Efficiency experiment.

Copies a large file from stdin to /dev/null using read()/write() with
varying BUFFSIZE values.  Measures user CPU, system CPU, wall-clock time,
and the number of read() loops.

Cache-control strategy
----------------------
We use posix_fadvise(POSIX_FADV_DONTNEED) after each run to evict the
input file from the page cache.  This works without root privileges and
without copying the file.  The fadvise call is issued from Python (via
os.posix_fadvise) right before each run.  If you have root you can
additionally echo 3 > /proc/sys/vm/drop_caches.
"""

import os
import re
from pathlib import Path

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext

# Dataset constants
DATASET_SIZE = 516_581_760  # bytes (~493 MiB) - matches APUE table
DATASET_NAME = "apue_input.dat"

_SRC_DIR = Path(__file__).resolve().parent / "src"


def _generate_dataset(dest: Path) -> None:
    """Create a deterministic file of exactly DATASET_SIZE bytes."""
    import random

    rng = random.Random(42)
    chunk = 1 << 20  # 1 MiB
    remaining = DATASET_SIZE
    with open(dest, "wb") as f:
        while remaining > 0:
            n = min(chunk, remaining)
            f.write(rng.randbytes(n))
            remaining -= n


def _drop_page_cache(path: Path) -> None:
    """Evict *path* from the page cache using posix_fadvise (no root needed)."""
    try:
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
    except (OSError, AttributeError):
        pass


class ApueIOBench:
    """
    Benchkit (new core protocol) benchmark for the APUE I/O efficiency
    experiment.

    Protocol steps:
      - fetch: generate the deterministic input dataset
      - build: compile apue_copy.c with -DBUFFSIZE=<value>
      - run:   execute the binary with stdin from dataset, stdout to /dev/null
      - collect: parse timing and loop count from the captured output
    """

    def fetch(
        self,
        ctx: FetchContext,
    ) -> FetchResult:
        """Generate the dataset and return src_dir."""
        src_dir = _SRC_DIR
        workdir = src_dir.parent / "workdir"
        workdir.mkdir(parents=True, exist_ok=True)

        dataset = workdir / DATASET_NAME
        if not dataset.exists() or dataset.stat().st_size != DATASET_SIZE:
            print(f"[apue_io] Generating dataset ({DATASET_SIZE} bytes) ...")
            _generate_dataset(dataset)
            print(f"[apue_io] Dataset ready: {dataset}")

        return FetchResult(src_dir=src_dir)

    def build(
        self,
        ctx: BuildContext,
        buffsize: int,
    ) -> BuildResult:
        """Compile apue_copy.c with the given BUFFSIZE."""
        src_dir = ctx.fetch_result.src_dir
        workdir = src_dir.parent / "workdir"
        build_dir = workdir / f"build_{buffsize}"
        build_dir.mkdir(parents=True, exist_ok=True)
        binary = build_dir / "apue_copy"
        src_file = src_dir / "apue_copy.c"

        ctx.exec(
            argv=[
                "gcc",
                "-O2",
                "-Wall",
                f"-DBUFFSIZE={buffsize}",
                str(src_file),
                "-o",
                str(binary),
            ],
            cwd=build_dir,
            output_is_log=True,
        )

        return BuildResult(
            build_dir=build_dir,
            other={"binary": str(binary)},
        )

    def run(
        self,
        ctx: RunContext,
        buffsize: int,
    ) -> RunResult:
        """
        Run the apue_copy binary timed by /usr/bin/time.

        We use a shell one-liner so that:
          - stdin comes from the dataset file
          - program stdout goes to /dev/null
          - program stderr (LOOPS=...) and /usr/bin/time stderr both get
            redirected to the shell's stdout, which ctx.exec captures.
        """
        build_dir = ctx.build_result.build_dir
        binary = ctx.build_result.other["binary"]
        workdir = build_dir.parent
        dataset = workdir / DATASET_NAME

        # Evict the dataset from page cache before each run for fairness.
        _drop_page_cache(dataset)

        # Shell command: time wraps the binary; stderr is merged into stdout
        # so ctx.exec can capture LOOPS=... and TIME_* lines.
        time_fmt = r"TIME_USER=%U\nTIME_SYS=%S\nTIME_ELAPSED=%e"
        shell_cmd = (
            f'/usr/bin/time -f "{time_fmt}" ' f"{binary} " f"< {dataset} " f"2>&1 " f"> /dev/null"
        )

        out = ctx.exec(
            argv=["/bin/sh", "-c", shell_cmd],
            cwd=build_dir,
            print_output=False,
        )

        return RunResult(outputs=[out])

    def collect(
        self,
        ctx: CollectContext,
        buffsize: int,
    ) -> RecordResult:
        """Parse LOOPS, TIME_USER, TIME_SYS, TIME_ELAPSED from the run output."""
        output = ctx.run_result.outputs[-1].stdout

        result: RecordResult = {}

        m = re.search(r"LOOPS=(\d+)", output)
        if m:
            result["loops"] = int(m.group(1))

        m = re.search(r"TIME_USER=([\d.]+)", output)
        if m:
            result["user_s"] = float(m.group(1))

        m = re.search(r"TIME_SYS=([\d.]+)", output)
        if m:
            result["sys_s"] = float(m.group(1))

        m = re.search(r"TIME_ELAPSED=([\d.:]+)", output)
        if m:
            elapsed_str = m.group(1)
            parts = elapsed_str.split(":")
            if len(parts) == 3:
                result["elapsed_s"] = (
                    float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                )
            elif len(parts) == 2:
                result["elapsed_s"] = float(parts[0]) * 60 + float(parts[1])
            else:
                result["elapsed_s"] = float(parts[0])

        elapsed = result.get("elapsed_s", 0)
        if elapsed > 0:
            result["throughput_mib_s"] = round(DATASET_SIZE / (1024 * 1024) / elapsed, 2)

        return result
