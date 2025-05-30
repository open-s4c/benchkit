#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run benchmarks from dacapobench.
"""


from benchkit.commandwrappers.jvmxlog import JVMXlogWrap
from benchmark_dacapobench import dacapobench_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import caller_dir
from benchkit.commandwrappers.perf import PerfReportWrap, PerfStatWrap, enable_non_sudo_perf
from benchkit.platforms import get_current_platform


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    # Where is the benchmark code located
    dacapobench_src_dir = (caller_dir() / "deps/dacapobench/benchmarks/").resolve()

    # Define the "perf-stat" command wrapper to be passed to the benchmark initialization
    # It is used to collect information from the PMCs.
    # perfstatwrap = PerfStatWrap(events=["cache-misses"])
    perfstatwrap = PerfStatWrap(
            perf_path=None,
            events=[
                # "cache-misses",
                "context-switches"
                # "sched:sched_switch"
                ],
            use_json = False,
            wrap_command = False,
            separator=";",
            quiet=False,
            remove_absent_event=False,
            )

    jvmxlogwrap = JVMXlogWrap()

    perfreportwrap = PerfReportWrap(
            wrap_command = False,
            perf_record_options = ["-e", "syscalls:sys_enter_futex,syscalls:sys_exit_futex"],
            perf_report_options = [],
            report_file = True,
            report_interactive = False,
            script = True,
            use_jvm = True,
            )

    # Define the campaign, associated with the LevelDB benchmark
    campaign = dacapobench_campaign(
        src_dir=dacapobench_src_dir,
        size=("small",),
        # size=("default",),
        # size=("large",),
        bench_names=[
            # "avrora",
            # "batik",
            # "biojava",
            # "cassandra",
            # "eclipse",
            # "fop",
            # "graphchi",
            # "h2",
            # "jme",
            # "jython",
            # "kafka",
            # "luindex",
            # "lusearch",
            # "pmd",
            # "spring",
            # "sunflow",
            # "tomcat",
            # "tradebeans",
            # "tradesoap",
            "xalan",
            "zxing",

            # "h2o", # Not supported due missing data
        ],
        nb_runs=2,
        benchmark_duration_seconds=3,
        # nb_threads=[4],
        nb_threads=[1, 2, 4],
        command_wrappers=[perfstatwrap, jvmxlogwrap, perfreportwrap],
        post_run_hooks=[perfstatwrap.post_run_hook_update_results, jvmxlogwrap.post_run_hook_update_results, perfreportwrap.post_run_hook_report],
        enable_data_dir=True,
        clean_in_between_different_benchmarks = True,
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_graph(
        plot_name="catplot",
        x="nb_threads",
        y="duration",
        col="bench_name",
        kind="bar",
    )

    # Generate a graph to visualize the output of perf stat
    suite.generate_graph(
        plot_name="speedup-stack",
    )


if __name__ == "__main__":
    main()
