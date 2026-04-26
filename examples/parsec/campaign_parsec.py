#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run benchmarks from PARSEC.
"""


from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import enable_non_sudo_perf
from benchkit.commandwrappers.speedupstack import SpeedupStackWrapper
from benchkit.lwchart import time_transformation
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import caller_dir, get_curdir
from examples.parsec.benchmark_parsec import parsec_campaign


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    # Where is the benchmark code located
    parsec_src_dir = (caller_dir() / "deps/parsec-benchmark/").resolve()

    libbpf_tools_dir = (get_curdir(__file__) / "deps/bcc/libbpf-tools/").resolve()

    thread_profiler_dir = (get_curdir(__file__) / "deps/thread-profiler-bpf").resolve()

    speedupstackwrapper = SpeedupStackWrapper(
        libbpf_tools_dir,
        thread_profiler_dir,
        # granularity=int(1e8),
        output_duration=True,
    )

    # Define the campaign, associated with the LevelDB benchmark
    campaign = parsec_campaign(
        src_dir=parsec_src_dir,
        # input=("simsmall",),
        # input=("simmedium",),
        input=("simlarge",),
        # input=("native",),
        # input=("simsmall", "simmedium", "simlarge",),
        bench_names=[
            # "blackscholes",
            # "bodytrack",
            # "canneal",  # TODO: fix benchmarking thread heuristic
            # "dedup", # TODO: heuristic
            # "facesim",
            # "ferret",
            # "fluidanimate",
            # "freqmine",  # TODO: heuristic (no clue if thread parameter does something)
            # "streamcluster",
            # "swaptions",
            # "vips",  # TODO: heuristic
            # "x264",  # TODO: heuristic (Very weird profile)
            "splash2x.barnes",
            # "splash2x.cholesky",
            # "splash2x.fft",
            # "splash2x.fmm",
            # "splash2x.lu_cb",
            # "splash2x.lu_ncb",
            # "splash2x.ocean_cp",
            # "splash2x.ocean_ncp",
            # "splash2x.radiosity",
            # "splash2x.radix",
            # "splash2x.raytrace",
            # "splash2x.water_nsquared",
            # "splash2x.water_spatial",
        ],
        nb_runs=1,
        # benchmark_duration_seconds=3,
        nb_threads=[1, 2, 4, 8],
        command_wrappers=([speedupstackwrapper] + speedupstackwrapper.command_wrappers()),
        command_attachments=speedupstackwrapper.command_attachments(),
        pre_run_hooks=speedupstackwrapper.pre_run_hooks(),
        post_run_hooks=speedupstackwrapper.post_run_hooks(),
        enable_data_dir=True,
        # Makes sure not to clear the deps between benchmarks.
        # This decreases compile time while increasing space requirements.
        clean_in_between_different_benchmarks=False,
        # Makes sure that the latest results are symlinked to a consistent folder.
        symlink_latest=True,
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # suite.generate_graph(
    #     plot_name="catplot",
    #     x="nb_threads",
    #     y="duration",
    #     col="bench_name",
    #     kind="bar",
    #     use_json=True,
    # )

    suite.generate_graph(
        title="Thread Event Profile",
        plot_name="thread-profile",
        speedupstackwrapper=speedupstackwrapper,
        show_run_number=1,
    )

    suite.generate_graph(
        title="Thread Event Profile",
        plot_name="thread-profile",
        speedupstackwrapper=speedupstackwrapper,
        show_run_number=2,
    )

    suite.generate_graph(
        title="Thread Event Profile",
        plot_name="thread-profile",
        speedupstackwrapper=speedupstackwrapper,
        show_run_number=3,
    )

    suite.generate_graph(
        title="Thread Event Profile for 8 Threads",
        plot_name="thread-profile",
        speedupstackwrapper=speedupstackwrapper,
        show_run_number=4,
    )

    suite.generate_graph(
        title="Speedup Stack",
        plot_name="speedup-stack",
        duration_transformation=lambda d: time_transformation(d, "ns", "ns"),
        speedup_stack_components={
            "threadprofiler_mutex_ns": lambda d, nb_t: d,
            "threadprofiler_futex_ns": lambda d, nb_t: d,
            "threadprofiler_offcpu_ns": lambda d, nb_t: d,
            "threadprofiler_disk_io_ns": lambda d, nb_t: d,
            "threadprofiler_initialization_ns": lambda d, nb_t: d,
            "threadprofiler_literature_load_imbalance_ns": lambda d, nb_t: d,
            "threadprofiler_cpi_overhead_ns": lambda d, nb_t: d,
        },
        # facet_by="input",
        # constant_duration=True,
        # speed_metric="operations/second",
    )


if __name__ == "__main__":
    main()
