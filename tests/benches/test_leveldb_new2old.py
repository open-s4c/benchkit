# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.benches.leveldb import LevelDBBench
from benchkit.core.compat.new2old import CampaignCartesianProduct


def main() -> None:
    parameter_space = {
        "bench_name": ["readrandom", "seekrandom"],
        "nb_threads": [2, 4, 8],
    }

    campaign = CampaignCartesianProduct(
        benchmark=LevelDBBench(),
        parameter_space=parameter_space,
    )

    campaign.run()

    campaign.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="bench_name",
    )


if __name__ == "__main__":
    main()
