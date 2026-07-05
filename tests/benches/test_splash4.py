# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Example usage of the SPLASH-4 benchmark with the new benchkit protocol.

Mirrors tests/benches/test_rocksdb.py: it validates the benchmark, then runs the
full fetch -> build -> run -> collect workflow, first with explicit context
threading and then with the more concise ctx.call() approach.
"""

from pathlib import Path
from pprint import pprint

from benchkit.benches.splash4 import SPLASH4_COMMIT, Splash4Bench
from benchkit.core.benchmark import Benchmark
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.core.validatebench import validate_benchmark

BENCHMARK = "fft"
NB_THREADS = 4


def main() -> None:
    bench: Benchmark = Splash4Bench()
    validate_benchmark(bench=bench)

    deps_dir = Path("~/.benchkit/benches").expanduser().resolve()

    # --- Explicit approach -------------------------------------------------
    fc = FetchContext.from_args(fetch_args={"parent_dir": deps_dir, "commit": SPLASH4_COMMIT})
    fr = bench.fetch(ctx=fc, **fc.fetch_args)

    bc = BuildContext.from_fetch(ctx=fc, fetch_result=fr, build_args={"benchmark": BENCHMARK})
    br = bench.build(ctx=bc, **bc.build_args)

    # benchmark is a *build* variable; run recovers the kernel from build_result.
    ra = {"nb_threads": NB_THREADS}
    rc = RunContext.from_build(ctx=bc, build_result=br, run_args=ra, duration_s=1)
    rr = bench.run(rc, **rc.run_args)

    cc = CollectContext.from_run(ctx=rc, run_result=rr)
    result = bench.collect(ctx=cc)
    pprint(result)

    # --- Alternative: ctx.call() (less plumbing) ---------------------------
    fc = FetchContext.from_args(fetch_args={"parent_dir": deps_dir, "commit": SPLASH4_COMMIT})
    fr = fc.call(bench.fetch)

    bc = BuildContext.from_fetch(ctx=fc, fetch_result=fr, build_args={"benchmark": BENCHMARK})
    br = bc.call(bench.build)

    ra = {"benchmark": BENCHMARK, "nb_threads": NB_THREADS}
    rc = RunContext.from_build(ctx=bc, build_result=br, run_args=ra, duration_s=1)
    rr = rc.call(bench.run)

    cc = CollectContext.from_run(ctx=rc, run_result=rr)
    result = cc.call(bench.collect)
    pprint(result)


if __name__ == "__main__":
    main()
