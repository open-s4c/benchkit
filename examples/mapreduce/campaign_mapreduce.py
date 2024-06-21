#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Example of campaign script for Metis/MapReduce benchmark.
"""

import sys

from mapreduce import metis_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir


def main() -> None:
    """Main function of the campaign script."""
    metis_src_dir = (get_curdir(__file__) / "deps/Metis/").resolve()

    if not metis_src_dir.is_dir():
        print(
            (
                "Please download Metis first:\n"
                "  cd examples/mapreduce\n"
                "  mkdir deps/\n"
                "  cd deps/\n"
                "  git clone https://github.com/ydmao/Metis.git\n"
                "  git checkout e5b04e2aa53301de71f0f5193f36e88c82008e6f"
            ),
            file=sys.stderr,
        )
        exit(1)

    campaign = metis_campaign(src_dir=metis_src_dir)

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
