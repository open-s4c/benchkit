#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from bench import Dat3mBench
from dat3m import standalone_dat3m_builder
from pythainer.runners import ConcreteDockerRunner

from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform


def get_local_docker_platform(docker_runner: ConcreteDockerRunner) -> Platform:
    docker_comm = DockerCommLayer(docker_runner=docker_runner)
    platform = Platform(comm_layer=docker_comm)
    return platform


def get_dat3m_docker_platform() -> Platform:
    dat3m_builder = standalone_dat3m_builder()
    # TODO building images does not support yet remote, the plan would be to give an optional shell_out callback
    # to that build() function and provide with the platform.shell from the selected host.
    dat3m_builder.build()
    dar3m_runner = dat3m_builder.get_runner()
    platform = get_local_docker_platform(docker_runner=dar3m_runner)
    return platform


def main():
    nb_runs = 3

    dat3m_platform = get_dat3m_docker_platform()

    dat3m_bench = Dat3mBench(
        src_dir="",  # TODO src_dir to mount in docker to access user client codes?
        platform=dat3m_platform,
    )

    campaign = CampaignCartesianProduct(
        name="dat3mlocks",
        benchmark=dat3m_bench,
        nb_runs=nb_runs,
        variables={
            "memory_model": ["aarch64"],
            "target_arch": ["arm8"],
            "lock_name": list(dat3m_bench.dat3m_locks),
            "bound": [None, 1, 3],
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
        title=f"dat3m locks verification time ({nb_runs} runs)",
        y="lock_name",
        x="benchkit/runtime_s",
        hue="bound",
        nan_replace=False,
    )


if __name__ == "__main__":
    main()
