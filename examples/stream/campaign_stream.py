#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for STREAM benchmark.
"""

from stream import stream_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""
    stream_src_dir = (get_curdir(__file__) / "deps/STREAM/").resolve()

    campaign = stream_campaign(
        name="stream",
        benchmark=None,
        src_dir=stream_src_dir,
        build_dir=None,
        results_dir=None,
        command_wrappers=[],
        command_attachments=[],
        shared_libs=[],
        pre_run_hooks=[],
        post_run_hooks=[],
        nb_runs=1,
        array_size=[10],
        master_thread_core=[0],
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=False,
        continuing=False,
    )

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
