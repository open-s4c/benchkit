#!/usr/bin/env python3

from benchkit.commandwrappers.perf import PerfReportWrap
from cgol_cpu import cgol_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir

def create_campaign_for_version(perf_assignment_path, flamegraph_path, version_nr):
    code_src_path = perf_assignment_path / f"version-{version_nr}"
    wrapper = PerfReportWrap(
        flamegraph_path=flamegraph_path, 
        perf_record_options=["--call-graph", "dwarf", "-g", "--all-user"]
    )

    campaign = cgol_campaign(
        command_wrappers= [
            wrapper
        ],
        post_run_hooks= [
            wrapper.post_run_hook_flamegraph
        ],
        src_dir=code_src_path,
        build_dir=code_src_path / "build",
        bench_name=["generation_based"],
        nb_threads=[4],
        size=[500],
        nb_generations=[5],
        nb_runs=1,
        enable_data_dir=True,
        constants= {
            "bench_version": f"version-{version_nr}"
        }
    )
    return campaign

def main() -> None:
    """Main function of the campaign script."""

    # Where is the benchmark code located
    perf_assignment_src = (get_curdir(__file__).parent.parent.parent.parent).resolve()
    flamegraph_path="../../../../FlameGraph"

    # Define the campaign
    campaign_1 = create_campaign_for_version(perf_assignment_src, flamegraph_path, 1)
    campaign_2 = create_campaign_for_version(perf_assignment_src, flamegraph_path, 2)
    campaign_3 = create_campaign_for_version(perf_assignment_src, flamegraph_path, 3)
    campaign_4 = create_campaign_for_version(perf_assignment_src, flamegraph_path, 4)
    campaign_5 = create_campaign_for_version(perf_assignment_src, flamegraph_path, 5)

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [
        campaign_1,
        campaign_2,
        campaign_3,
        campaign_4,
        campaign_5,
    ]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

if __name__ == "__main__":
    main()
