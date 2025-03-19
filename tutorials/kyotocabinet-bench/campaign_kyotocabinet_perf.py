#!/usr/bin/env python3
# Copyright (C) 2025 lelele group. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for kyotocabinet benchmarks using perf-stat collecting libvsync locks data.
"""

from pathlib import Path
from typing import Iterable, Tuple


from kyotocabinet import kyotocabinet_campaign
from tiltlib import TiltLib
from benchkit.commandwrappers.perf import  PerfStatWrap
from benchkit.campaign import (
    CampaignCartesianProduct,
    CampaignSuite,
    Platform,
    get_current_platform,
)
from benchkit.sharedlibs import SharedLib
from benchkit.sharedlibs.precompiled import PrecompiledSharedLib
from benchkit.utils.dir import caller_dir, get_curdir

# Get the directory of the current script
this_dir = caller_dir()

# Set the directories for tilt locks and vsync dependencies
tilt_locks_dir = (this_dir / "../../examples/tilt/locks").resolve()
vsync_dir = (tilt_locks_dir / "../deps/libvsync/").resolve()


patch_path = (tilt_locks_dir / "prefetch.diff").resolve()


def build_locks(platform: Platform) -> Tuple[Path, Path]:
    """
    Build tilt locks and libvsync versions for different platforms.
    
    :param platform: Current platform object
    :return: Returns two paths: one is the directory of the successful build, 
             and the other is the regression test version directory (not used in this test)
    """
    
    # Create TiltLib instance to build the normal version of tilt lock
    tilt_ok = TiltLib(tilt_locks_dir=tilt_locks_dir, build_prefix="build_ok")
    
    
    platform.comm.shell(
        command="git checkout -- include/vsync/atomic/internal/arm64.h",
        current_dir=vsync_dir,
    )
    tilt_ok.build() 
    build_ok = tilt_ok.build_dir  # Get the path of the successful build

    
    tilt_reg = TiltLib(tilt_locks_dir=tilt_locks_dir, build_prefix="build_reg")
    
    
    platform.comm.shell(command=f"git apply {patch_path}", current_dir=vsync_dir)
    tilt_reg.build()  
    build_regression = tilt_reg.build_dir  

    # Return the two build directories
    return build_ok, build_regression


def get_campaign(
    shared_libs: Iterable[SharedLib],
    mutex_constant: str,
) -> CampaignCartesianProduct:
    """
    Create a benchmark campaign specifying shared libraries and the type of lock.
    
    :param shared_libs: Shared libraries to use
    :param mutex_constant: Lock type constant
    :return: Returns a campaign instance
    """
    # Set the Kyoto Cabinet source code directory
    kyotocabinet_src_dir = (get_curdir(__file__) / "deps/kyotocabinet-1.2.76/").resolve()

    # Configure perf-stat wrapper to collect performance data
    perfstatwrap = PerfStatWrap(
        events=[
            "cache-references", "cache-misses", 
        ], 
        separator=";"  
    )

    # Configure campaign, set shared libraries and lock type constant
    return kyotocabinet_campaign(
        src_dir=kyotocabinet_src_dir,  # Kyoto Cabinet source path
        test_name=[],  # Test name is empty, meaning a custom benchmark
        shared_libs=shared_libs,  # Set shared libraries
        constants={
            "mutex": mutex_constant,  
        },
        nb_runs=3,  
        benchmark_duration_seconds=10,  
        nb_threads=[1, 2, 4, 8, 16, 32, 64],  
        command_wrappers=[perfstatwrap],  # Use perf-stat for performance analysis
        post_run_hooks=[perfstatwrap.post_run_hook_update_results],  # Update results after run
        enable_data_dir=True,  
    )


def get_baseline_campaign() -> CampaignCartesianProduct:
    """
    Create a baseline benchmark campaign using pthread_mutex lock.
    
    :return: Returns the campaign instance using pthread_mutex lock
    """
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

def get_vcaslock_nolse_campaign(build_path: Path) -> CampaignCartesianProduct:
    vcaslocklib_path = (build_path / "libvcaslock-nolse.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (VSync, no LSE)",
        shared_libs=[PrecompiledSharedLib(path=vcaslocklib_path, env_vars=None)],
    )

def get_vcaslock_nolse_prefetch_campaign(build_path: Path) -> CampaignCartesianProduct:
    vcaslocklib_path = (build_path / "libvcaslock-nolse.so").resolve()
    return get_campaign(
        mutex_constant="CAS lock (VSync, no LSE, prefetch)",
        shared_libs=[PrecompiledSharedLib(path=vcaslocklib_path, env_vars=None)],
    )



def main() -> None:

    platform = get_current_platform()
    hostname = platform.hostname  
    
    # Build normal and regression versions of the tilt lock
    build_ok, build_regression = build_locks(platform=platform)
    
    # Create multiple campaign instances, testing baseline lock and VSync lock
    campaigns = [
        get_baseline_campaign(),  
        get_caslock_campaign(build_path=build_ok),
        get_vcaslock_nolse_campaign(build_path=build_ok),
        get_vcaslock_nolse_prefetch_campaign(build_path=build_regression),
        
    ]
    
    
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()  
    suite.run_suite()  

    
    suite.generate_global_csv()
    
    
    title = f"kyotocabinet using tilt locks - Host: {hostname}"

    # Generate a line plot to compare throughput of different lock types
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

    # Generate a scatter plot to compare throughput of different lock types
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
