#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for LevelDB benchmarks using different locks.
"""

from pathlib import Path
from typing import Iterable, Tuple

from leveldb import leveldb_campaign
from tiltlib import TiltLib

from benchkit.campaign import (
    CampaignCartesianProduct,
    CampaignSuite,
    Platform,
    get_current_platform,
)
from benchkit.sharedlibs import SharedLib
from benchkit.sharedlibs.precompiled import PrecompiledSharedLib
from benchkit.utils.dir import caller_dir, get_curdir

this_dir = caller_dir()
tilt_locks_dir = (this_dir / "../../examples/tilt/locks").resolve()
vsync_dir = (tilt_locks_dir / "../deps/libvsync/").resolve()
patch_path = (tilt_locks_dir / "prefetch.diff").resolve()


def build_locks(platform: Platform) -> Tuple[Path, Path]:
    tilt_ok = TiltLib(tilt_locks_dir=tilt_locks_dir, build_prefix="build_ok")
    platform.comm.shell(
        command="git checkout -- include/vsync/atomic/internal/arm64.h",
        current_dir=vsync_dir,
    )
    tilt_ok.build()
    build_ok = tilt_ok.build_dir

    tilt_reg = TiltLib(tilt_locks_dir=tilt_locks_dir, build_prefix="build_reg")
    platform.comm.shell(command=f"git apply {patch_path}", current_dir=vsync_dir)
    tilt_reg.build()
    build_regression = tilt_reg.build_dir

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


def get_taslock_campaign(build_path: Path) -> CampaignCartesianProduct:
    taslocklib_path = (build_path / "libtaslock.so").resolve()
    return get_campaign(
        mutex_constant="TAS lock (std atomic)",
        shared_libs=[PrecompiledSharedLib(path=taslocklib_path, env_vars=None)],
    )


def get_caslock_campaign(build_path: Path) -> CampaignCartesianProduct:
    caslocklib_path = (build_path / "libcaslock.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (std atomic)",
        shared_libs=[PrecompiledSharedLib(path=caslocklib_path, env_vars=None)],
    )


def get_vcaslock_nolse_campaign(build_path: Path) -> CampaignCartesianProduct:
    vcaslocklib_path = (build_path / "libvcaslock-nolse.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (VSync, no LSE)",
        shared_libs=[PrecompiledSharedLib(path=vcaslocklib_path, env_vars=None)],
    )


def get_vcaslock_lse_campaign(build_path: Path) -> CampaignCartesianProduct:
    vcaslocklib_path = (build_path / "libvcaslock-lse.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (VSync, LSE)",
        shared_libs=[PrecompiledSharedLib(path=vcaslocklib_path, env_vars=None)],
    )


def get_vcaslock_nolse_prefetch_campaign(build_path: Path) -> CampaignCartesianProduct:
    vcaslocklib_path = (build_path / "libvcaslock-nolse.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (VSync, no LSE, prefetch)",
        shared_libs=[PrecompiledSharedLib(path=vcaslocklib_path, env_vars=None)],
    )


def get_vcaslock_lse_prefetch_campaign(build_path: Path) -> CampaignCartesianProduct:
    vcaslocklib_path = (build_path / "libvcaslock-lse.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (VSync, LSE, prefetch)",
        shared_libs=[PrecompiledSharedLib(path=vcaslocklib_path, env_vars=None)],
    )


def main() -> None:
    platform = get_current_platform()
    hostname = platform.hostname
    build_ok, build_regression = build_locks(platform=platform)
    campaigns = [
        get_baseline_campaign(),
        get_taslock_campaign(build_path=build_ok),
        get_caslock_campaign(build_path=build_ok),
        get_vcaslock_nolse_campaign(build_path=build_ok),
        get_vcaslock_lse_campaign(build_path=build_ok),
        get_vcaslock_nolse_prefetch_campaign(build_path=build_regression),
        get_vcaslock_lse_prefetch_campaign(build_path=build_regression),
    ]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_global_csv()

    title = f"LevelDB readrandom w/wo tilt locks - Host: {hostname}"
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
