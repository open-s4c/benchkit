#!/usr/bin/env python3
# Copyright (C) 2025 lelele group. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Example of campaign script for Kyoto Cabinet benchmark benchmarks using LD_PRELOAD switch libvsync and calling graph by fzf.
"""

from pathlib import Path
from typing import Iterable, Tuple

from kyotocabinet import kyotocabinet_campaign
from tiltlib import TiltLib
from benchkit.commandwrappers.perf import PerfReportWrap
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
    
    # Create a TiltLib instance to build the normal version of tilt lock
    tilt_ok = TiltLib(tilt_locks_dir=tilt_locks_dir, build_prefix="build_ok")
    
    # Switch the arm64.h file in the vsync directory
    platform.comm.shell(
        command="git checkout -- include/vsync/atomic/internal/arm64.h",
        current_dir=vsync_dir,
    )
    tilt_ok.build()  # Perform the build
    build_ok = tilt_ok.build_dir  # Get the path of the successful build

    # Return the build directories
    return build_ok


def main() -> None:
    """
    Main function to execute Kyoto Cabinet benchmark tests, using libvsync and tilt locks for performance analysis.
    """
    
    platform = get_current_platform()
    hostname = platform.hostname  
    
    # Build the normal and regression versions of tilt locks
    build_ok = build_locks(platform=platform)
    
    # Set the source code directory for Kyoto Cabinet
    kyotocabinet_src_dir = (get_curdir(__file__) / "deps/kyotocabinet-1.2.76/").resolve()
    
    # Set the path to FlameGraph for generating flame graphs
    flamegraph_path = caller_dir() / "deps/FlameGraph"
    
    perf_wrapper = PerfReportWrap(
        freq=10,  
        report_interactive=False,  # Disable interactive report
        report_file=True,  # Generate a report file
        flamegraph_path=flamegraph_path,  # Set the flamegraph path
    )
    
    # Set the path to the built libvmuslmutex.so library
    vcaslocklib_path = (build_ok / "libvcaslock-nolse.so").resolve()
    
    campaign = kyotocabinet_campaign(
        src_dir=kyotocabinet_src_dir,  
        test_name=[],  # Test name is empty, meaning custom benchmark
        shared_libs=[PrecompiledSharedLib(path=vcaslocklib_path, env_vars=None)],  # Use precompiled shared library
        constants={
            "mutex": "CAS lock (VSync, no LSE)",  
        },
        nb_runs=3,  
        benchmark_duration_seconds=10,  
        nb_threads=[1, 2, 4],  
        command_wrappers=[perf_wrapper],  # Use perf wrapper to collect performance data
        
        post_run_hooks=[
            perf_wrapper.post_run_hook_report,  # Generate performance report
            perf_wrapper.post_run_hook_flamegraph,  # Generate flame graph
        ],
        enable_data_dir=True,  
    )
    
    campaigns = [campaign]  
    suite = CampaignSuite(campaigns=campaigns)  
    suite.print_durations() 
    suite.run_suite()  
    
    # Use fzf for fuzzy searching to view the perf report and flame graph
    results_path = campaign.base_data_dir()  
    perf_wrapper.fzf_report(search_dir=results_path)  
    perf_wrapper.fzf_flamegraph(search_dir=results_path)  


if __name__ == "__main__":
    main()
