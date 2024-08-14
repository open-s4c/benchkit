#!/usr/bin/env python3
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for LevelDB benchmarks using different locks.
"""

from pathlib import Path
from typing import Iterable, Tuple

from leveldb import leveldb_campaign

from benchkit.campaign import (
    CampaignCartesianProduct,
    CampaignSuite,
    Platform,
    get_current_platform,
)
from benchkit.sharedlibs import SharedLib
from benchkit.sharedlibs.precompiled import PrecompiledSharedLib
from benchkit.utils.dir import caller_dir, get_curdir


tiltlocks_dir = caller_dir() / "tiltlocks"
vsync_dir = (tiltlocks_dir / "../deps/libvsync/").resolve()


def build_locks(platform: Platform) -> Tuple[Path, Path]:
    build_cmd = "cmake -DCMAKE_BUILD_TYPE=Release .."

    platform.comm.shell(
        command="git checkout -- include/vsync/atomic/internal/arm64.h",
        current_dir=vsync_dir,
    )
    build_ok = (tiltlocks_dir / "build_ok").resolve()
    platform.comm.makedirs(path=build_ok, exist_ok=True)
    platform.comm.shell(command=build_cmd, current_dir=build_ok)
    platform.comm.shell(command="make", current_dir=build_ok)

    platform.comm.shell(command="git apply ../../tiltlocks/prefetch.diff", current_dir=vsync_dir)
    build_regression = (tiltlocks_dir / "build_reg").resolve()
    platform.comm.makedirs(path=build_regression, exist_ok=True)
    platform.comm.shell(command=build_cmd, current_dir=build_regression)
    platform.comm.shell(command="make", current_dir=build_regression)

    return build_ok, build_regression


def get_campaign(
    shared_libs: Iterable[SharedLib],
    mutex_constant: str,
) -> CampaignCartesianProduct:
    leveldb_src_dir = (get_curdir(__file__) / "deps/leveldb/").resolve()

    return leveldb_campaign(
        src_dir=leveldb_src_dir,
        bench_name=[
            "readrandom",
        ],
        shared_libs=shared_libs,
        constants={
            "mutex": mutex_constant,
        },
        nb_runs=3,
        benchmark_duration_seconds=10,
        nb_threads=[1, 2, 4, 8, 16, 24, 32, 48, 64, 72, 96, 128, 138, 180, 200, 256],
    )


def get_baseline_campaign() -> CampaignCartesianProduct:
    return get_campaign(
        mutex_constant="pthread_mutex",
        shared_libs=[],
    )


def get_caslock_campaign(build_path: Path) -> CampaignCartesianProduct:
    caslocklib_path = (build_path / "libcaslock.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (std atomic)",
        shared_libs=[PrecompiledSharedLib(path=caslocklib_path, env_vars=None)],
    )


def get_vcaslock_campaign(build_path: Path) -> CampaignCartesianProduct:
    vcaslocklib_path = (build_path / "libvcaslock.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (VSync)",
        shared_libs=[PrecompiledSharedLib(path=vcaslocklib_path, env_vars=None)],
    )


def get_vcaslock_prefetch_campaign(build_path: Path) -> CampaignCartesianProduct:
    vcaslocklib_path = (build_path / "libvcaslock.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (VSync, prefetch)",
        shared_libs=[PrecompiledSharedLib(path=vcaslocklib_path, env_vars=None)],
    )


def main() -> None:
    platform = get_current_platform()
    build_ok, build_regression = build_locks(platform=platform)
    campaigns = [
        get_baseline_campaign(),
        get_caslock_campaign(build_path=build_ok),
        get_vcaslock_campaign(build_path=build_ok),
        get_vcaslock_prefetch_campaign(build_path=build_regression),
    ]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    title = "LevelDB readrandom w/wo tilt locks"
    suite.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="mutex",
        style="mutex",
        markers=True,
        dashes=False,
        title=title,
    )
    suite.generate_graph(
        plot_name="scatterplot",
        x="nb_threads",
        y="throughput",
        hue="mutex",
        style="mutex",
        title=title,
    )


if __name__ == "__main__":
    main()
