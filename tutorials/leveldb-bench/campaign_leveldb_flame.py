#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for LevelDB benchmarks, generating one flamegraph per record.
"""

from leveldb import leveldb_campaign

from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import PerfReportWrap, enable_non_sudo_perf
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import caller_dir, get_curdir


def main() -> None:
    """Main function of the campaign script."""
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    # Where is the benchmark code located
    leveldb_src_dir = (get_curdir(__file__) / "deps/leveldb/").resolve()

    # Where is the FlameGraph repo located
    flamegraph_path = caller_dir() / "deps/FlameGraph"

    # Define the "perf-record" command wrapper to be passed to the benchmark initialization.
    # It is used to collect information from the PMCs, to later generate the associated flamegraph.
    perf_wrapper = PerfReportWrap(
        freq=99,
        # freq=10,
        report_interactive=False,
        report_file=True,
        flamegraph_path=flamegraph_path,
    )

    # Define the campaign, associated with the LevelDB benchmark,
    # coupling the benchmark with the perf wrapper.
    campaign = leveldb_campaign(
        src_dir=leveldb_src_dir,
        bench_name=[
            "readrandom",
        ],
        nb_runs=1,
        benchmark_duration_seconds=3,
        nb_threads=[1, 8, 16],
        command_wrappers=[perf_wrapper],
        post_run_hooks=[
            perf_wrapper.post_run_hook_report,
            perf_wrapper.post_run_hook_flamegraph,
        ],
        enable_data_dir=True,
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Fuzzy search in terminal though the perf reports and the flamegraphs
    results_path = campaign.base_data_dir()
    perf_wrapper.fzf_report(search_dir=results_path)
    perf_wrapper.fzf_flamegraph(search_dir=results_path)


if __name__ == "__main__":
    main()
