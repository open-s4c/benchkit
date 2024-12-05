#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run NPB benchmark.
"""


from typing import Iterable, List

from npb import NPBBench

from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.utils.dir import caller_dir


def npb_campaign(
    benchmark_duration_seconds: int = 3,
    nb_runs: int = 3,
    test_names: List[str] = ("lu", "bt", "cg"),
    t_classes: List[str] = ("A", "B", "C"),
    nb_threads: Iterable[int] = (4, 4, 8),
) -> CampaignCartesianProduct:
    _npb_src_dir = (caller_dir() / "deps/npb").resolve()

    bench = NPBBench(src_dir=_npb_src_dir)

    campaign = CampaignCartesianProduct(
        name="npb",
        benchmark=bench,
        nb_runs=nb_runs,
        variables={
            "test_name": test_names,
            "t_class": t_classes,
            "nb_threads": nb_threads,
        },
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=benchmark_duration_seconds,
    )

    return campaign


def main() -> None:
    campaigns = [
        npb_campaign(),
    ]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
