# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.benches.leveldb import LevelDBBench
from benchkit.core.compat.new2old import CampaignIterateVariables


def main() -> None:
    variables = [
        {"bench_name": "readrandom", "nb_threads": 2},
        {"bench_name": "readrandom", "nb_threads": 8},
        {"bench_name": "seekrandom", "nb_threads": 4},
    ]

    campaign = CampaignIterateVariables(
        benchmark=LevelDBBench(),
        variables=variables,
    )

    campaign.run()

    campaign.generate_graph(
        plot_name="scatterplot",
        x="nb_threads",
        y="throughput",
        hue="bench_name",
    )


if __name__ == "__main__":
    main()
