#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Example of campaign script for Memcached benchmark.
"""

from kit.memcached_benchmark import memcached_campaign

from benchkit.campaign import CampaignSuite
from benchkit.utils.dir import get_curdir
from benchkit.platforms import get_current_platform


def main() -> None:
    """Main function of the campaign script."""
    memtier_benchmark_src_dir = (get_curdir(__file__) / "deps/memtier_benchmark/").resolve()
    memcached_src_dir = (get_curdir(__file__) / "deps/memcached/").resolve()

    memtier_benchmark_platform = get_current_platform()
    memcached_platform = get_current_platform()

    campaign = memcached_campaign(nb_threads=[2, 4, 5, 10],
                                  nb_runs=5,
                                  client_src_dir=memtier_benchmark_src_dir,
                                  server_src_dir=memcached_src_dir,
                                  server_platform=memtier_benchmark_platform,
                                  client_platform=memcached_platform)

    campaigns = [campaign]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()
    suite.generate_graph(plot_name="barplot", x="nb_threads", y="Totals Ops/sec")


if __name__ == "__main__":
    main()
