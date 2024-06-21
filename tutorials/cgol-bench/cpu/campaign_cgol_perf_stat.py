#!/usr/bin/env python3

from benchkit.commandwrappers.perf import PerfStatWrap
from cgol_cpu import cgol_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir

# Creates a campaign for a specific version of the code
def create_campaign_for_version(perf_assignment_dir, version_nr):
    version_src_dir = perf_assignment_dir / f"version-{version_nr}"
    wrapper = PerfStatWrap(separator=";", events=["instructions", "cache-misses", "cache-references"])

    campaign = cgol_campaign(
        command_wrappers= [
            wrapper
        ],
        post_run_hooks= [
            wrapper.post_run_hook_update_results
        ],
        src_dir=version_src_dir,
        build_dir=version_src_dir / "build",
        bench_name=["generation_based"],
        nb_threads=[4],
        size=[5000],
        nb_generations=[30],
        nb_runs=30,
        enable_data_dir=True,
        constants= {
            "bench_version": f"version-{version_nr}"
        }
    )
    return campaign

def main() -> None:
    """Main function of the campaign script."""

    # Root directory where the Conway's Game of Life implementation is located
    perf_assignment_dir = (get_curdir(__file__).parent.parent.parent.parent).resolve()

    # Define the campaign for the different CPU versions
    campaign_1 = create_campaign_for_version(perf_assignment_dir, 1)
    campaign_2 = create_campaign_for_version(perf_assignment_dir, 2)
    campaign_3 = create_campaign_for_version(perf_assignment_dir, 3)
    campaign_4 = create_campaign_for_version(perf_assignment_dir, 4)
    campaign_5 = create_campaign_for_version(perf_assignment_dir, 5)
    campaign_6 = create_campaign_for_version(perf_assignment_dir, 6)
    campaign_7 = create_campaign_for_version(perf_assignment_dir, 7)

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [
        campaign_1,
        campaign_2,
        campaign_3,
        campaign_4,
        campaign_5,
        campaign_6,
        campaign_7
    ]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate graphs with the results
    suite.generate_graph(
        plot_name="barplot",
        x="bench_version",
        y="perf-stat/instructions",
        hue="bench_version",
    )

    suite.generate_graph(
        plot_name="barplot",
        x="bench_version",
        y="perf-stat/cache-misses",
        hue="bench_version",
    )

    suite.generate_graph(
        plot_name="barplot",
        x="bench_version",
        y="perf-stat/cache-references",
        hue="bench_version",
    )

if __name__ == "__main__":
    main()
