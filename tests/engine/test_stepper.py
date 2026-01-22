# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pathlib import Path
from pprint import pprint

from benchkit.benches.rocksdb import RocksDBBench
from benchkit.engine.stepper import Stepper
from benchkit.platforms import get_current_platform


def main() -> None:
    bench = RocksDBBench()
    platform = get_current_platform()
    args = {
        "parent_dir": Path("~/.benchkit/benches").expanduser().resolve(),
        "commit": "v10.7.5",
        "bench_name": "readrandom",
        "nb_threads": 7,
    }
    duration_s = 1

    stepper = Stepper(bench=bench, platform=platform)
    session = stepper.fetch(args=args)
    session = stepper.build(session=session, args=args)
    session = stepper.run(session=session, args=args, duration_s=duration_s)
    session = stepper.collect(session=session, args=args)
    result = session.record_result
    pprint(result)


if __name__ == "__main__":
    main()
