#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run tilt locks.
"""


from tiltlib import SimpleMutexTestBench as Bench
from tiltlib import TiltLib

from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.utils.dir import caller_dir

campaign_dir = caller_dir()
tilt_locks_dir = campaign_dir / "locks"
bench_src_dir = campaign_dir / "bench"
vsync_dir = (tilt_locks_dir / "../deps/libvsync/").resolve()


def main() -> None:
    tiltlib = TiltLib(tilt_locks_dir=tilt_locks_dir)
    tiltlib.build()

    campaigns = [
        CampaignCartesianProduct(
            name="tilt",
            benchmark=Bench(
                src_dir=bench_src_dir,
                shared_libs=[tiltlib],
            ),
            nb_runs=1,
            variables={
                "lock": ["", "taslock", "caslock", "vcaslock-nolse", "vcaslock-lse"],
            },
            constants=None,
            debug=False,
            gdb=False,
            enable_data_dir=True,
            continuing=False,
        ),
    ]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
