#!/usr/bin/env python3
# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run benchmarks from Rodinia.
"""


from itertools import product

from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import enable_non_sudo_perf
from benchkit.commandwrappers.speedupstack import SpeedupStackWrapper
from benchkit.lwchart import time_transformation
from benchkit.platforms import get_current_platform
from benchkit.utils.dir import caller_dir, get_curdir
from examples.rodinia.benchmark_rodinia import rodinia_campaign


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    # Where is the benchmark code located
    rodinia_src_dir = (caller_dir() / "deps/rodinia/openmp/").resolve()

    libbpf_tools_dir = (get_curdir(__file__) / "deps/bcc/libbpf-tools/").resolve()

    thread_profiler_dir = (get_curdir(__file__) / "deps/thread-profiler-bpf").resolve()

    speedupstackwrapper = SpeedupStackWrapper(
        libbpf_tools_dir,
        thread_profiler_dir,
        output_duration=True,
    )

    nb_threads = [1, 2, 4, 8, 16]
    vars = [
        # {
        #     "bench_name": "bfs",
        #     "size": ["4M", "8M", "16M", "32M"],
        # },
        {
            "bench_name": "heartwall",
            "size": [5, 10, 20, 40],
        },
        # {
        #     "bench_name": "lud",
        #     "size": [256, 512, 2048],
        # },
        # {
        #     "bench_name": "needle",
        #     "size": [5000, 10000, 20000, 35000],
        # },
        # {
        #     "bench_name": "srad",
        #     "size": [25, 50, 100],
        # },
    ]

    def unfold_vars(vars_list, thread_list):
        result = []

        for v in vars_list:
            for t in thread_list:
                base = {**v, "nb_threads": t}

                keys = base.keys()
                values = [val if isinstance(val, list) else [val] for val in base.values()]

                for combo in product(*values):
                    result.append(dict(zip(keys, combo)))

        return result

    # __import__("pprint").pprint(unfold_vars(vars, nb_threads))

    # Define the campaign, associated with the Rodinia benchmark
    campaign = rodinia_campaign(
        src_dir=rodinia_src_dir,
        variables=unfold_vars(vars, nb_threads),
        nb_runs=1,
        command_wrappers=([speedupstackwrapper] + speedupstackwrapper.command_wrappers()),
        command_attachments=speedupstackwrapper.command_attachments(),
        pre_run_hooks=speedupstackwrapper.pre_run_hooks(),
        post_run_hooks=speedupstackwrapper.post_run_hooks(),
        enable_data_dir=True,
        # Makes sure that the latest results are symlinked to a consistent folder.
        symlink_latest=True,
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # suite.generate_graph(
    #     title="Thread Event Profile",
    #     plot_name="thread-profile",
    #     speedupstackwrapper=speedupstackwrapper,
    #     show_run_number=1,
    # )

    # suite.generate_graph(
    #     title="Thread Event Profile",
    #     plot_name="thread-profile",
    #     speedupstackwrapper=speedupstackwrapper,
    #     show_run_number=2,
    # )

    # suite.generate_graph(
    #     title="Thread Event Profile",
    #     plot_name="thread-profile",
    #     speedupstackwrapper=speedupstackwrapper,
    #     show_run_number=3,
    # )

    # suite.generate_graph(
    #     title="Thread Event Profile for 8 Threads",
    #     plot_name="thread-profile",
    #     speedupstackwrapper=speedupstackwrapper,
    #     show_run_number=4,
    # )

    suite.generate_graph(
        title="Speedup Stack",
        plot_name="speedup-stack",
        duration_transformation=lambda d: time_transformation(d, "ns", "ns"),
        speedup_stack_components=[
            {
                "threadprofiler_mutex_ns": lambda d, nb_t: d,
                "threadprofiler_futex_ns": lambda d, nb_t: d,
                "threadprofiler_offcpu_ns": lambda d, nb_t: d,
                "threadprofiler_disk_io_ns": lambda d, nb_t: d,
                "threadprofiler_initialization_ns": lambda d, nb_t: d,
                "threadprofiler_literature_load_imbalance_ns": lambda d, nb_t: d,
                "threadprofiler_cpi_overhead_ns": lambda d, nb_t: d,
            }
        ],
        facet_by="size",
    )


if __name__ == "__main__":
    main()
