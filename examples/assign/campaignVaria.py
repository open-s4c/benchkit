#!/usr/bin/env python3
from benchkit.commandwrappers.perf import PerfStatWrap, PerfReportWrap

from kit.ParalelInPlace import ParallelInPlace_campaign
from kit.ParalelInPlaceOffset import ParallelInPlaceOffset_campaign
from kit.ParalelIntPoolCircularOfsetAlignedSingleVec import ParallelIntPoolCircularOfsetAlignedSingleVec_campaign
from kit.ParalelInPlaceFollowing import ParallelInPlaceFollowing_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir
from benchkit.utils.types import PathType
from benchkit.benchmark import PreRunHook, RecordResult
from benchkit.platforms import *
from pathlib import Path

import os


def main() -> None:
    """Main function of the campaign script."""


    def remove_data(
        experiment_results_lines,
        record_data_dir,
        write_record_file_fun,):

        get_current_platform().comm.shell(
            command=f"rm -f perf.data",
            shell=True,
            split_arguments=False,
            current_dir=record_data_dir,
            output_is_log=True,
        )



    build_dir=Path(__file__).parent.resolve()/"code"


    wrapper1 = PerfReportWrap(flamegraph_path="../../../FlameGraph",
			      perf_record_options=["--call-graph","dwarf","-g","--all-user", "-D -1", "--control=fifo:/tmp/perf_ctl.fifo,/tmp/perf_ctl_ack.fifo"])
    wrapper2 = PerfStatWrap(separator=";", events=["alignment-faults"])
    nb_runs = 10
    itterations = [200]
    cores = [1,4,6]
    size = [20000]
    # Define the campaign, associated with the LevelDB benchmark
    campaignParallelInPlace = ParallelInPlace_campaign(
        command_wrappers= [
            wrapper1,wrapper2
        ],
        post_run_hooks= [
	        wrapper2.post_run_hook_update_results,
            remove_data
        ],
	    build_dir=build_dir,
        itterations=itterations,
        size=size,
        cores=cores,
        enable_data_dir=True,
        constants = {"name":"ParallelInPlace"},
        nb_runs = nb_runs
        )
    campaignParallelInPlaceOffset = ParallelInPlaceOffset_campaign(
        command_wrappers= [
            wrapper1,wrapper2
        ],
        post_run_hooks= [
	        wrapper2.post_run_hook_update_results,
            remove_data
        ],
	    build_dir=build_dir,
        itterations=itterations,
        size=size,
        cores=cores,
        enable_data_dir=True,
        constants = {"name":"ParallelInPlaceOffset"},
        nb_runs = nb_runs
        )
    campaignParallelIntPoolCircularOfsetAlignedSingleVec = ParallelIntPoolCircularOfsetAlignedSingleVec_campaign(
        command_wrappers= [
            wrapper1,wrapper2
        ],
        post_run_hooks= [
	        wrapper2.post_run_hook_update_results,
            remove_data
        ],
        build_dir=build_dir,
        itterations=itterations,
        size=size,
        cores=cores,
        enable_data_dir=True,
        constants = {"name":"ParallelIntPoolCircularOfsetAlignedSingleVec"},
        nb_runs = nb_runs
        )
    ParallelInPlaceFollowing = ParallelInPlaceFollowing_campaign(
        command_wrappers= [
            wrapper1,wrapper2
        ],
        post_run_hooks= [
	        wrapper2.post_run_hook_update_results,
            remove_data
        ],
	    build_dir=build_dir,
        itterations=itterations,
        size=size,
        cores=cores,
        locks=[4,],
        enable_data_dir=True,
        constants = {"name":"ParallelInPlaceFollowing"},
        nb_runs = nb_runs
        )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaignParallelIntPoolCircularOfsetAlignedSingleVec,campaignParallelInPlace,campaignParallelInPlaceOffset,ParallelInPlaceFollowing]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate a graph to visualize the results
    suite.generate_graph(
        plot_name="barplot",
        x="cores",
        y="throughput",
        hue="name"
    )


if __name__ == "__main__":
    main()
