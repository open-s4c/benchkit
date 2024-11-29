#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal campaign to run trace-cmd wrapper.
"""


from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.commandwrappers.tracecmd import TraceCmdWrap
from benchmarks.threadmig import ThreadMigrationBench


def main() -> None:
    tracecmd_wrap = TraceCmdWrap(
        tracecmd_prefix="/home/antonio/Downloads/tracecmd/trace-cmd-v3.3.1/tracecmd/",
        events=["sched"],
    )

    campaigns = [
        CampaignCartesianProduct(
            name="tilt",
            benchmark=ThreadMigrationBench(
                command_wrappers=[tracecmd_wrap],
            ),
            nb_runs=1,
            variables={},
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
