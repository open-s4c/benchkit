#!/usr/bin/env python3

from cgol import cgol_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir

def main() -> None:
    """Main function of the campaign script."""

    # Where is the benchmark code located
    cgol_src = (get_curdir(__file__).parent.parent.parent).resolve()

    # Define the campaign, associated with the LevelDB benchmark
    campaign = cgol_campaign(
        src_dir=cgol_src,
        bench_name=["time_based"],
        nb_threads=[1,2,3,4],
        width=[200],
        height=[200],
        version=["version-1", "version-2", "version-3", "version-4", "version-5"],
        benchmark_duration_seconds=10,
        nb_runs=3,
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    suite.generate_graph(
        plot_name="barplot",
        x="nb_threads",
        y="throughput",
        hue="version",
    )

if __name__ == "__main__":
    main()
