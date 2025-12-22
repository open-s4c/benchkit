# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Example usage of the RocksDB benchmark with the new benchkit protocol.

This script demonstrates two approaches for running benchmarks:
1. Explicit approach: Manually calling each phase and unpacking arguments
2. Context.call() approach: Using context's call() method for automatic argument passing

Both approaches produce identical results, with the call() method being more concise.
"""

from pathlib import Path
from pprint import pprint

from benchkit.benches.rocksdb import RocksDBBench
from benchkit.core.benchmark import Benchmark
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.core.validatebench import validate_benchmark


def main() -> None:
    """
    Run the RocksDB benchmark using both explicit and call() approaches.

    Demonstrates the complete benchmark workflow:
    1. Validate the benchmark implementation
    2. Fetch the source code
    3. Build the benchmark
    4. Run a workload
    5. Collect and print results
    """
    # Calling benchmark methods explicitly
    bench: Benchmark = RocksDBBench()
    validate_benchmark(bench=bench)

    this_dir = Path(__file__).parent.resolve()
    deps_dir = this_dir / "deps"

    fc = FetchContext.from_args(fetch_args={"parent_dir": deps_dir, "commit": "v10.7.5"})
    fr = bench.fetch(ctx=fc, **fc.fetch_args)

    bc = BuildContext.from_fetch(ctx=fc, fetch_result=fr, build_args={})
    br = bench.build(ctx=bc, **bc.build_args)  # TODO perhaps add debug/release as arg?

    ra = {"bench_name": "readrandom", "nb_threads": 3}
    rc = RunContext.from_build(ctx=bc, build_result=br, run_args=ra, duration_s=1)
    rr = bench.run(rc, **rc.run_args)

    cc = CollectContext.from_run(ctx=rc, run_result=rr)
    result = bench.collect(ctx=cc, bench_name="readrandom")

    pprint(result)

    # Alternative (less plumbing):
    fc = FetchContext.from_args(fetch_args={"parent_dir": deps_dir, "commit": "v10.7.5"})
    fr = fc.call(bench.fetch)

    bc = BuildContext.from_fetch(ctx=fc, fetch_result=fr, build_args={})
    br = bc.call(bench.build)

    ra = {"bench_name": "readrandom", "nb_threads": 3}
    rc = RunContext.from_build(ctx=bc, build_result=br, run_args=ra, duration_s=1)
    rr = rc.call(bench.run)

    cc = CollectContext.from_run(ctx=rc, run_result=rr)
    result = cc.call(bench.collect)

    pprint(result)


if __name__ == "__main__":
    main()
