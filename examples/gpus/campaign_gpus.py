#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT


from addvec import AddVecBench
from gpus import get_gpu_docker_platform

from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.utils.dir import caller_dir


def main() -> None:
    nb_runs = 3
    guest_src_dir = "/home/user/project"

    platform = get_gpu_docker_platform(
        host_src_dir=(caller_dir() / "src").resolve(),
        guest_src_dir=guest_src_dir,
    )

    bench = AddVecBench(
        platform=platform,
        src_dir=guest_src_dir,
    )

    campaign = CampaignCartesianProduct(
        name="gpuaddvec",
        benchmark=bench,
        nb_runs=nb_runs,
        variables={
            "block_size": [1, 2, 16, 256, 2048, 4096, 8192, 16384, 32768],
        },
        constants={},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    campaign_suite = CampaignSuite(campaigns=[campaign])
    campaign_suite.run_suite()

    campaign_suite.generate_graph(
        plot_name="barplot",
        title=f"Add vector on GPU ({nb_runs} runs)",
        y="kernel_compute_seconds",
        x="block_size",
    )


if __name__ == "__main__":
    main()
