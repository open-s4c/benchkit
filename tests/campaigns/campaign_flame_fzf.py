#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
from benchkit import CampaignCartesianProduct
from benchkit.benches.small.dd import DDBench
from benchkit.commandwrappers.perf import PerfRecordWrap, enable_non_sudo_perf
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import get_tools_dir


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    flamegraph_dir = get_tools_dir(None) / "FlameGraph"
    perf_wrapper = PerfRecordWrap(
        freq=99,
        report_interactive=False,
        report_file=True,
        flamegraph_path=flamegraph_dir,
    )
    perf_wrapper.fetch_flamegraph()

    def flame_post_hook(
        experiment_results_lines,
        record_data_dir,
        write_record_file_fun,
    ):
        return perf_wrapper.post_run_hook_flamegraph(
            experiment_results_lines=experiment_results_lines,
            record_data_dir=record_data_dir,
            write_record_file_fun=write_record_file_fun,
            flamegraph_width=400,
            flamegraph_fontsize=14,
        )

    campaign = CampaignCartesianProduct(
        name="flame_dd_fzf",
        benchmark=DDBench(),
        variables={"block_count": [50, 500]},
        nb_runs=1,
        command_wrappers=[perf_wrapper],
        post_run_hooks=[
            perf_wrapper.post_run_hook_report,
            flame_post_hook,
        ],
        platform=platform,
    )

    campaign.run()

    results_path = campaign.base_data_dir()
    perf_wrapper.fzf_report(search_dir=results_path)
    perf_wrapper.fzf_flamegraph(search_dir=results_path)


if __name__ == "__main__":
    main()
