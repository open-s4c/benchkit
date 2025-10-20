#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
from typing import Dict, Iterable, Optional

from heater_sequential import HeaterSeqBench

from benchkit.benchmark import CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.helpers.linux.predictable.cpupower import CPUPower
from benchkit.platforms import Platform, get_current_platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.dir import get_curdir
from benchkit.utils.types import PathType


def heater_seq_campaign(
    name: str = "leveldb_campaign",
    benchmark: Optional[HeaterSeqBench] = None,
    src_dir: Optional[PathType] = None,
    build_dir: Optional[str] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    cpu: Iterable[int] = (0),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the LevelDB benchmark."""
    variables = {
        "cpu": cpu,
    }

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = HeaterSeqBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
            build_dir=build_dir,
        )

    return CampaignCartesianProduct(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        constants=constants,
        debug=debug,
        gdb=gdb,
        enable_data_dir=enable_data_dir,
        continuing=continuing,
        benchmark_duration_seconds=benchmark_duration_seconds,
        results_dir=results_dir,
        pretty=pretty,
    )


def main() -> None:
    """Main function of the campaign script."""

    # to get the frequencies
    cpuPower = CPUPower()

    # Where is the benchmark code located
    leveldb_src_dir = (get_curdir(__file__) / "").resolve()

    # print(cpuPower.get_frequency_values(range(0, os.cpu_count())))

    # Define the campaign, associated with the LevelDB benchmark
    campaign = heater_seq_campaign(
        src_dir=leveldb_src_dir,
        nb_runs=3,
        benchmark_duration_seconds=3,
        cpu=range(0, os.cpu_count()),
        # frequency=cpuPower.get_frequency_values(range(0, os.cpu_count())),
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate a graph to visualize the results
    suite.generate_graph(
        plot_name="barplot",
        x="cpu",
        y="ops",
        title=f"Sequential Heater on {get_current_platform().comm.hostname()}",
    )


if __name__ == "__main__":
    main()
