#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT


from pathlib import Path
from typing import List

from addvec import AddVecBench
from gpus import get_gpu_docker_platform
from nsightwrappers import NcuWrap, NsysWrap
from platforms import Platform

from benchkit.benchmark import PostRunHook
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.commandwrappers import CommandWrapper
from benchkit.utils.dir import caller_dir

nb_runs = 1
guest_project_dir = Path("/home/user/project")


def get_campaign(
    platform: Platform,
    wrappers: List[CommandWrapper],
    post_run_hooks: List[PostRunHook],
) -> CampaignCartesianProduct:
    campaign = CampaignCartesianProduct(
        name="gpuaddvec",
        benchmark=AddVecBench(
            platform=platform,
            src_dir=guest_project_dir / "src",
            command_wrappers=wrappers,
            post_run_hooks=post_run_hooks,
        ),
        nb_runs=nb_runs,
        variables={
            "block_size": [256],
        },
        constants={},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    return campaign


def main() -> None:
    platform = get_gpu_docker_platform(
        host_src_dir=caller_dir().resolve(),
        guest_src_dir=guest_project_dir,
    )

    nsys_wrap = NsysWrap(platform=platform)
    ncu_wrap = NcuWrap(platform=platform)

    campaign_nsys = get_campaign(
        platform=platform,
        wrappers=[nsys_wrap],
        post_run_hooks=[nsys_wrap.post_run_hook],
    )

    campaign_ncu = get_campaign(
        platform=platform,
        wrappers=[ncu_wrap],
        post_run_hooks=[ncu_wrap.post_run_hook],
    )

    campaign_suite = CampaignSuite(
        campaigns=[
            campaign_nsys,
            campaign_ncu,
        ]
    )
    campaign_suite.run_suite()


if __name__ == "__main__":
    main()
