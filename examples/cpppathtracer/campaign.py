# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from typing import Dict, List

from cpppathtracer import BUILD_VARIABLES, RUN_VARIABLES, RayTracerBenchmark

from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.commandwrappers.perf import PerfStatWrap, enable_non_sudo_perf
from benchkit.platforms import Platform, get_current_platform, get_remote_platform

RUN_REMOTELY = False
REMOTE_ADDR = "ssh://root@example.com:2222"


class ForgetFullException(Exception):
    pass


def create_campaign(
    variables: Dict[str, List[str]],
    copy_src_to_build: bool,
    nb_runs: int,
    source_dir: str,
    bench_src_dir: str,
    platform: Platform | None = None,
):
    perfstat_wrapper = PerfStatWrap(
        freq=1000,
        separator=";",
        events=["cache-misses", "branch-misses"],
    )

    benchmark = RayTracerBenchmark(
        src_dir=source_dir,
        copy_src_to_build=copy_src_to_build,
        bench_src_dir=bench_src_dir,
        command_wrappers=[
            perfstat_wrapper,
        ],
        platform=platform,
        post_run_hooks=[
            perfstat_wrapper.post_run_hook_update_results,
        ],
    )

    return CampaignCartesianProduct(
        name="Raytracer_benchmark",
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        gdb=False,
        debug=False,
        constants=None,
        enable_data_dir=True,
    )


def main():
    source_dir = "./CppPathTracer"
    bench_src_dir = "./CppPathTracer"
    copy_src_to_build = False

    if RUN_REMOTELY:
        platform = get_remote_platform(REMOTE_ADDR)
        bench_src_dir = "/tmp/CppPathTracer"
        copy_src_to_build = True
    else:
        platform = get_current_platform()

    enable_non_sudo_perf(platform.comm)

    # The variables that have to be iterated through for the benchmark

    variables = {
        "nb_threads": [16],
        "preset": ["fast_cornell_benchmark"],
        "threading_implementation": [2],
        "use_color_buffer_per_thread": [0],
        "triangle_intersection_algo": [1],
        "work_square_size": [1],
        "aabb_hit_implementation": [3],
        "bvh_first_hit_caching": [1],
        "bvh_sah": [1],
    }

    nb_runs = 5

    # This is just as a safety to make sure the variables specified
    # and passed to the cartesian product below are actually all used
    # in the benchmark.
    # Why? I am forgetfull and I wasted like 2 benchmark hours because
    # of
    for v in variables.keys():
        if v not in BUILD_VARIABLES + RUN_VARIABLES:
            raise ForgetFullException("You forgot to use the variables set here in the benchmark")

    campaign = create_campaign(
        variables=variables,
        copy_src_to_build=copy_src_to_build,
        nb_runs=nb_runs,
        source_dir=source_dir,
        bench_src_dir=bench_src_dir,
        platform=platform,
    )
    campaigns = [campaign]

    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
