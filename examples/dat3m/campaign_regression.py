#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from bench import Dat3mBench
from dat3m import get_dat3m_docker_platform
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite


considered_dat3m_versions = {
    "v4.1.0": "4.1.0",
    "8237954ad": "8237954ad41afa8c18ce68c9cf0303dc68b000d8",
}
nb_runs = 3
selected_target = "arm8"
selected_bound = 1
memory_models = [
    "aarch64",
    "c11",
    "c11-orig",
    "imm",
    "linux-kernel",
    "lkmm-no-data-race",
    "rc11",
    "sc",
]


def main():
    campaigns = []
    for dat3m_version_name, dat3m_commit in considered_dat3m_versions.items():
        dat3m_platform = get_dat3m_docker_platform(
            version_acronym=dat3m_version_name,
            dat3m_commit=dat3m_commit,
        )
        dat3m_bench = Dat3mBench(src_dir="", platform=dat3m_platform)

        print("Available targets: ", dat3m_bench.dat3m_targets)
        print("Available MM: ", dat3m_bench.dat3m_memorymodels)

        campaign = CampaignCartesianProduct(
            name="dat3mlocks",
            benchmark=dat3m_bench,
            nb_runs=nb_runs,
            variables={
                "memory_model": memory_models,
                "target_arch": [selected_target],
                "lock_name": list(dat3m_bench.dat3m_locks),
                "bound": [selected_bound],
            },
            constants={
                "version": dat3m_version_name,
            },
            debug=False,
            gdb=False,
            enable_data_dir=True,
            continuing=False,
            benchmark_duration_seconds=None,
        )
        campaigns.append(campaign)

    campaign_suite = CampaignSuite(campaigns=campaigns)
    campaign_suite.run_suite()
    campaign_suite.generate_global_csv()
    campaign_suite.generate_graph(
        plot_name="catplot",
        title=f"dat3m locks verification time (target {selected_target}, {nb_runs} runs)",
        kind="bar",
        col="memory_model",
        x="lock_name",
        y="benchkit/runtime_s",
        hue="version",
        nan_replace=False,
    )


if __name__ == "__main__":
    main()
