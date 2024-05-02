#!/usr/bin/env python3

from cgol_cpu import cgol_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir

def create_campaign_for_version(perf_assignment_path, version_nr):
    code_src_path = perf_assignment_path / f"version-{version_nr}"
    campaign = cgol_campaign(
        src_dir=code_src_path,
        build_dir=code_src_path / "build",
        bench_name=["time_based"],
        nb_threads=[1,2,3,4],
        size=[200],
        benchmark_duration_seconds=3,
        nb_runs=3,
        constants= {
            "bench_version": f"version-{version_nr}"
        }
    )
    return campaign

def main() -> None:
    """Main function of the campaign script."""

    # Where is the benchmark code located
    perf_assignment_src = (get_curdir(__file__).parent.parent.parent.parent).resolve()

    # Define the campaigns
    campaign_1 = create_campaign_for_version(perf_assignment_src, 1)
    campaign_2 = create_campaign_for_version(perf_assignment_src, 2)
    campaign_3 = create_campaign_for_version(perf_assignment_src, 3)
    campaign_4 = create_campaign_for_version(perf_assignment_src, 4)
    campaign_5 = create_campaign_for_version(perf_assignment_src, 5)

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [
        campaign_1,
        campaign_2,
        campaign_3,
        campaign_4,
        campaign_5
    ]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_graph(
        plot_name="barplot",
        x="nb_threads",
        y="throughput",
        hue="bench_version",
    )

if __name__ == "__main__":
    main()
