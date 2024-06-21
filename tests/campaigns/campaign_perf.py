#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchmarks.sleep import SleepBench

from benchkit.campaign import CampaignIterateVariables
from benchkit.commandwrappers.perf import PerfStatWrap, enable_non_sudo_perf
from benchkit.platforms import get_current_platform, get_remote_platform


def main() -> None:
    remote = False

    if remote:
        platform = get_remote_platform(host="laptop", environment=None)
    else:
        platform = get_current_platform()

    enable_non_sudo_perf(comm_layer=platform.comm)

    events = ["cache-misses", "instructions", "cycles"]
    perfstatwrap = PerfStatWrap(
        events=events,
        use_json=True,
        # separator=";",
        platform=platform,
    )

    CampaignIterateVariables(
        name="strace",
        benchmark=SleepBench(
            command_wrappers=[perfstatwrap],
            post_run_hooks=[perfstatwrap.post_run_hook_update_results],
            platform=platform,
        ),
        nb_runs=1,
        variables=[
            {
                "duration_seconds": 1,
            },
        ],
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
    ).run()


if __name__ == "__main__":
    main()
