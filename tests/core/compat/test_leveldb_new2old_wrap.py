# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.benches.leveldb import LevelDBBench
from benchkit.commandwrappers.taskset import TasksetWrap
from benchkit.core.compat.new2old import CampaignCartesianProduct


def main() -> None:
    parameter_space = {
        "bench_name": ["readrandom"],
        "nb_threads": [1],
        "master_thread_core": [0],
    }

    taskset_wrap = TasksetWrap()

    campaign = CampaignCartesianProduct(
        benchmark=LevelDBBench(),
        parameter_space=parameter_space,
        command_wrappers=[taskset_wrap],
        duration_s=5,
    )

    campaign.run()


if __name__ == "__main__":
    main()
