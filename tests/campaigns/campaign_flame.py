#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchmarks.sleep import SleepBench

from benchkit.campaign import CampaignIterateVariables
from benchkit.commandwrappers.perf import PerfReportWrap, enable_non_sudo_perf
from benchkit.platforms import get_current_platform
from benchkit.utils.git import clone_repo
from benchkit.utils.dir import caller_dir


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    flamegraph_path = caller_dir() / "deps/FlameGraph"
    clone_repo(
        repo_url="https://github.com/brendangregg/FlameGraph.git",
        repo_src_dir=flamegraph_path,
        commit="cd9ee4c4449775a2f867acf31c84b7fe4b132ad5",
    )

    perf_wrapper = PerfReportWrap(
        freq=99,
        # freq=10,
        report_interactive=False,
        report_file=True,
        flamegraph_path=flamegraph_path,
    )

    campaign = CampaignIterateVariables(
        name="flame",
        benchmark=SleepBench(
            command_wrappers=[perf_wrapper],
            post_run_hooks=[
                perf_wrapper.post_run_hook_report,
                perf_wrapper.post_run_hook_flamegraph,
            ],
        ),
        nb_runs=1,
        variables=[
            {
                "duration_seconds": 1,
            },
            {
                "duration_seconds": 2,
            },
        ],
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
    )

    campaign.run()

    results_path = campaign.base_data_dir()
    perf_wrapper.fzf_report(search_dir=results_path)
    perf_wrapper.fzf_flamegraph(search_dir=results_path)


if __name__ == '__main__':
    main()
