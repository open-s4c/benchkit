#!/usr/bin/env python3
from benchkit.commandwrappers.perf import PerfStatWrap, PerfReportWrap
from kit.IntVersion1 import intversion_campaign
from kit.LongIntVersion import longintversion_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir

def main() -> None:
    """Main function of the campaign script."""

    wrapper = PerfReportWrap(flamegraph_path="../../../FlameGraph")
    # Define the campaign, associated with the LevelDB benchmark
    campaignint = intversion_campaign(
        command_wrappers= [
            wrapper
        ],
        post_run_hooks= [
            wrapper.post_run_hook_flamegraph
        ],
        name="Campaignint",
        itterations=[100],
        size=[800],
        enable_data_dir=True,
        constants = {"name":"int"}
    )


    # Define the campaign, associated with the LevelDB benchmark
    campaignlong = longintversion_campaign(
        command_wrappers= [
            wrapper
        ],
        post_run_hooks= [
            wrapper.post_run_hook_flamegraph
        ],
        name="Campaignlong",
        itterations=[50,100],
        size=[60,80],
        enable_data_dir=True,
        constants = {"name":"longint"}
    )


    

    # Define the campaign suite and run the benchmarks in the suite
    campaigns = [campaignint, campaignlong]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()

    # Generate a graph to visualize the results
    suite.generate_graph(
        plot_name="barplot",
        x="size",
        y="throughput",
        hue="name"
    )


if __name__ == "__main__":
    main()
