#!/usr/bin/env python3

"""
Example of campaign script for Metis/MapReduce benchmark.
"""

from mapreduce import metis_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""
    metis_src_dir = (get_curdir(__file__) / "deps/Metis/").resolve()

    campaign = metis_campaign(post_run_hooks=[],command_wrappers=[], src_dir=metis_src_dir)

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
