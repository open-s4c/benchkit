#!/usr/bin/env python3

from benchkit.commandwrappers.perf import PerfStatWrap
from cgol import cgol_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir

def main() -> None:
    """Main function of the campaign script."""

    # Where is the benchmark code located
    cgol_src = (get_curdir(__file__).parent.parent.parent).resolve()
    wrapper = PerfStatWrap(separator=";", events=["system_time", "cache-misses"])

    # Define the campaign, associated with the LevelDB benchmark
    campaign = cgol_campaign(
        command_wrappers= [
            wrapper
        ],
        post_run_hooks= [
            wrapper.post_run_hook_update_results
        ],
        src_dir=cgol_src,
        bench_name=["generation_based"],
        nb_threads=[4],
        width=[200],
        height=[200],
        version=["version-1", "version-2", "version-3", "version-4", "version-5"],
        nb_generations=[1],
        nb_runs=1,
        enable_data_dir=True
    )

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

if __name__ == "__main__":
    main()
