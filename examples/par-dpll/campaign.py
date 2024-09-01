import os
import re
from pathlib import Path
from typing import Iterable, List

from benchmark import ParallelDPLL, SequentialDPLL

from benchkit.benchmark import Benchmark, RecordResult, WriteRecordFileFunction
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.commandwrappers.strace import StraceWrap
from benchkit.commandwrappers.valgrind import ValgrindWrapper
from benchkit.utils.types import PathType


def _parse_alloc_string(allocs_string: str) -> RecordResult:
    results = {}
    splitted = allocs_string.replace(",", "").removeprefix("total heap usage: ").split(" ")
    filtered_results = list(filter(lambda x: x.isnumeric(), splitted))
    assert len(filtered_results) == 3
    results["allocs"] = int(filtered_results[0])
    results["frees"] = int(filtered_results[1])
    results["bytes_allocated"] = int(filtered_results[2])
    return results


def _parse_results(results_out_file: PathType) -> RecordResult:
    val_output_string = open(results_out_file, "r").read()
    allocs_match = re.search(
        r"total heap usage: (\d+|,+)+ allocs, (\d+|,+)+ frees, (\d+|,+)+ bytes allocated",
        val_output_string,
    )
    if allocs_match is not None:
        return _parse_alloc_string(allocs_match.group(0))


def post_run_hook_valgrind_allocations(
    experiment_results_lines: List[RecordResult],
    record_data_dir: PathType,
    write_record_file_fun: WriteRecordFileFunction,
) -> RecordResult:
    """
    Post run hook to collect memory allocation from valgrind output.
    """
    assert experiment_results_lines
    assert write_record_file_fun

    output_name = "valgrind-out.txt"
    valgrind_out_path = os.path.join(record_data_dir, output_name)
    results = _parse_results(valgrind_out_path)
    for line in experiment_results_lines:
        if "runtime_s" in line:
            line["allocations_throughput"] = int(results["allocs"]) / line["runtime_s"]
    return results


def _parse_strace_futex(strace_out_path: str) -> RecordResult:
    strace_out = open(strace_out_path).read()
    num_futexes = re.search(r" \d*\.\d*\s*\d*\.\d*\s*\d*\s*\d*\s*\d*\s*futex", strace_out)

    if num_futexes is None:
        return {}
    else:
        num_futexes_str = num_futexes.group(0)
        data = [token for token in num_futexes_str.split(" ") if token != ""]
        assert len(data) >= 3
        return {
            "futex_percentage": data[0],
            "futex_time": data[1],
            "futex_usecs_calls": data[2],
            "futex_calls": data[3],
        }


def post_run_hook_extract_futex(
    experiment_results_lines: List[RecordResult],
    record_data_dir: PathType,
    write_record_file_fun: WriteRecordFileFunction,
) -> RecordResult:
    assert experiment_results_lines
    assert write_record_file_fun
    output_name = "strace.txt"
    strace_out_path = os.path.join(record_data_dir, output_name)
    return _parse_strace_futex(strace_out_path)


def create_campaign(
    name: str,
    nb_runs: int,
    benchmark: Benchmark,
    instances: Iterable[str] = (),
    num_threads: Iterable[int] = (),
    implementation_dirs: Iterable[str] = (),
) -> CampaignCartesianProduct:
    return CampaignCartesianProduct(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables={
            "instance": instances,
            "implementation": implementation_dirs,
            "num_threads": num_threads,
        },
        constants={},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=10,
    )


def main():
    implementation_dirs_seq = [
        "./sequential",
        "./better_allocations_sequential",
    ]

    implementation_dirs_par = [
        "./lock-free",
        "./pooled",
    ]

    nb_runs = 3
    vg_wrapper = ValgrindWrapper()
    instance_dir_sat = Path("./instances/sat_instances")
    instance_dir_unsat = Path("./instances/unsat_instances")

    instances_sat = [os.fspath(p.absolute()) for p in instance_dir_sat.iterdir()]
    instances_unsat = [os.fspath(p.absolute()) for p in instance_dir_unsat.iterdir()]

    ### Campaigns Init ###
    campaign_init_fast = create_campaign(
        name="Initial benchmarks sequential",
        nb_runs=nb_runs,
        benchmark=SequentialDPLL(src_dir="./"),
        instances=instances_sat[0:-2],
        implementation_dirs=["./sequential"],
    )
    campaign_init_slow = create_campaign(
        name="Initial benchmarks sequential",
        nb_runs=nb_runs,
        benchmark=SequentialDPLL(src_dir="./"),
        instances=instances_sat,
        implementation_dirs=["./sequential"],
    )
    campaign_valgrind = create_campaign(
        name="Valgrind",
        nb_runs=1,
        benchmark=SequentialDPLL(
            src_dir="./",
            post_run_hooks=[post_run_hook_valgrind_allocations],
            command_wrappers=[vg_wrapper],
        ),
        instances=instances_sat[0:1],
        implementation_dirs=["./sequential"],
    )
    campaign_valgrind_better_allocs = create_campaign(
        name="Valgrind",
        nb_runs=1,
        benchmark=SequentialDPLL(
            src_dir="./",
            post_run_hooks=[post_run_hook_valgrind_allocations],
            command_wrappers=[vg_wrapper],
        ),
        instances=instances_sat,
        implementation_dirs=["./better_allocations_sequential"],
    )
    campaign_seq_vs_ba_fast = create_campaign(
        name="Sequential vs Better allocs",
        nb_runs=nb_runs,
        benchmark=SequentialDPLL(src_dir="./"),
        instances=instances_sat[0:-2],
        implementation_dirs=implementation_dirs_seq,
    )
    campaign_seq_vs_ba_slow = create_campaign(
        name="Sequential vs Better allocs",
        nb_runs=nb_runs,
        benchmark=SequentialDPLL(src_dir="./"),
        instances=instances_sat[-2:],
        implementation_dirs=implementation_dirs_seq,
    )
    campaign_seq_vs_ba_fast_allocations_throughput = create_campaign(
        name="Allocations throughput Sequential vs Better allocs",
        nb_runs=1,
        benchmark=SequentialDPLL(
            src_dir="./",
            post_run_hooks=[post_run_hook_valgrind_allocations],
            command_wrappers=[vg_wrapper],
        ),
        instances=instances_sat[:-1],
        implementation_dirs=implementation_dirs_seq,
    )
    campaign_multithreaded_lock_free = create_campaign(
        name="Multithreaded lock-free",
        nb_runs=nb_runs,
        benchmark=ParallelDPLL(src_dir="./"),
        instances=instances_unsat,
        implementation_dirs=implementation_dirs_par,
        num_threads=[4],
    )
    campaign_multithreaded = create_campaign(
        name="Multithreaded queue size 100",
        nb_runs=nb_runs,
        benchmark=ParallelDPLL(src_dir="./"),
        instances=instances_unsat,
        implementation_dirs=["./pooled"],
        num_threads=[2, 4, 8],
    )
    campaign_multithreaded_strace = create_campaign(
        name="Multithreaded strace queue size 100",
        nb_runs=nb_runs,
        benchmark=ParallelDPLL(
            src_dir="./",
            command_wrappers=[StraceWrap(trace_forks=True)],
            post_run_hooks=[post_run_hook_extract_futex],
        ),
        instances=instances_unsat,
        implementation_dirs=["./pooled"],
        num_threads=[2, 4, 8],
    )

    ### Campaigns Runs ###
    campaigns = [
        campaign_init_fast,
        campaign_init_slow,
        campaign_valgrind,
        campaign_valgrind_better_allocs,
        campaign_seq_vs_ba_fast,
        campaign_seq_vs_ba_slow,
        campaign_seq_vs_ba_fast_allocations_throughput,
        campaign_multithreaded_lock_free,
        campaign_multithreaded,
        campaign_multithreaded_strace,
    ]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    ### Campaigns Graphs Generation ###
    campaign_init_fast.generate_graph(
        plot_name="barplot",
        title=f"Runtime sequential algorithm ({nb_runs})",
        y="runtime_s",
        x="instance",
        hue="implementation",
    )

    campaign_init_slow.generate_graph(
        plot_name="barplot",
        title=f"Runtime sequential algorithm ({nb_runs})",
        y="runtime_s",
        x="instance",
        hue="implementation",
    )

    campaign_valgrind.generate_graph(
        plot_name="barplot",
        title=f"Memory usage sequential algorithm ({nb_runs})",
        y="bytes_allocated",
        x="instance",
        hue="implementation",
    )

    campaign_valgrind_better_allocs.generate_graph(
        plot_name="barplot",
        title=f"Memory usage sequential algorithm better allocations ({nb_runs})",
        y="bytes_allocated",
        x="instance",
        hue="implementation",
    )
    campaign_valgrind_better_allocs.generate_graph(
        plot_name="barplot",
        title=f"Allocations sequential algorithm better allocations ({nb_runs})",
        y="allocs",
        x="instance",
        hue="implementation",
    )

    campaign_seq_vs_ba_fast.generate_graph(
        plot_name="barplot",
        title=f"Runtime Sequential vs Better allocation nb runs: {nb_runs}",
        y="runtime_s",
        x="instance",
        hue="implementation",
    )

    campaign_seq_vs_ba_slow.generate_graph(
        plot_name="barplot",
        title=f"Runtime Sequential vs Better allocation nb runs: {nb_runs}",
        y="runtime_s",
        x="instance",
        hue="implementation",
    )

    campaign_seq_vs_ba_fast_allocations_throughput.generate_graph(
        plot_name="barplot",
        title=f"Runtime Sequential vs Better allocation nb runs: {nb_runs}",
        y="allocations_throughput",
        x="instance",
        hue="implementation",
    )

    campaign_multithreaded_lock_free.generate_graph(
        plot_name="barplot",
        title=f"Runtime comparison lock-free and pooled nb_runs: {nb_runs}",
        y="runtime_s",
        x="instance",
        hue="implementation",
    )

    campaign_multithreaded.generate_graph(
        plot_name="barplot",
        title=f"Pooled version nb runs {nb_runs}",
        y="runtime_s",
        x="instance",
        hue="num_threads",
    )

    campaign_multithreaded_strace.generate_graph(
        plot_name="barplot",
        title=f"Pooled version nb runs {nb_runs}",
        y="futex_calls",
        x="instance",
        hue="num_threads",
    )

    campaign_multithreaded_strace.generate_graph(
        plot_name="barplot",
        title=f"Pooled version nb runs {nb_runs}",
        y="futex_time",
        x="instance",
        hue="num_threads",
    )
    campaign_multithreaded_strace.generate_graph(
        plot_name="barplot",
        title=f"Pooled version nb runs {nb_runs}",
        y="futex_percentage",
        x="instance",
        hue="num_threads",
    )


if __name__ == "__main__":
    main()
