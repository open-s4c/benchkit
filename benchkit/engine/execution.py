# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Execution engine for benchkit campaigns.

The `ExecutionEngine` owns the orchestration of campaign execution.
Today it hosts the current sequential behavior, moved verbatim from
`Campaign.campaign_run()`; the `Campaign*` classes delegate to it and keep
working exactly as before ("Campaigns describe, Engines execute").

Planned extensions land as separate slices on this class:

- `RecordGenerator`: parameter-space exploration as a pluggable policy;
- `ExecutionPolicy`: scheduling (sequential, parallel, portfolio, early-stop);
- `ResultStore`: storage layout (CSV/JSON/artifacts) out of `Benchmark`.

Until those land, the engine still delegates record iteration and CSV/JSON
writing to the legacy `Benchmark.run()` loop; the point of this class is to
be the single place where orchestration happens.
"""

import multiprocessing
import os
import pathlib
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from benchkit.campaign import Campaign


class ExecutionEngine:
    """
    Own the orchestration of campaign execution; sequential-only today.

    This is the Tier-2 entry point of the new API: advanced users compose an
    engine and run campaigns through it. The constructor currently takes no
    argument; future slices will add `generator=`, `policy=` and `store=`.

    Note: while `Campaign` transitions to a pure data structure, the engine
    reads some of its non-public members (benchmark, continuing/symlink
    flags, command-file bookkeeping). This protected access is deliberate
    and temporary: it disappears as those responsibilities migrate to the
    engine and its result store.
    """

    # pylint: disable=protected-access

    def run(
        self,
        campaign: "Campaign",
        *,
        other_campaigns_seconds: int = 0,
        barrier: Optional[multiprocessing.Barrier] = None,
    ) -> None:
        """
        Run a single campaign, possibly among other campaigns in a suite.

        Args:
            campaign (Campaign):
                the campaign to execute.
            other_campaigns_seconds (int, optional):
                time remaining to execute other campaigns in the suite.
                Defaults to 0.
            barrier (Optional[multiprocessing.Barrier], optional):
                if needed, the barrier used to synchronize different benchmarks.
                Defaults to None.
        """
        # Workaround to trunc this global file, before logging refactoring TODO
        campaign._init_cmd_file()

        csv_output_path = campaign.csv_output_abs_path()
        csv_output_dir = os.path.dirname(csv_output_path)
        os.makedirs(csv_output_dir, exist_ok=True)

        base_data_dir = campaign.base_data_dir()
        if campaign._symlink_latest and base_data_dir:
            symlink = str(csv_output_path).rsplit("_", 3)[0]
            base_data_dir = pathlib.Path(base_data_dir)
            symlink_path = pathlib.Path(symlink + "_latest")
            if symlink_path.exists(follow_symlinks=False):
                os.remove(symlink_path)
            os.symlink(base_data_dir, symlink_path, True)
            # Create a `results.csv` symlink inside of the data directory
            # that links to the to the results CSV file.
            abs_data_dir_result_path = base_data_dir / "results.csv"
            os.symlink(csv_output_path, abs_data_dir_result_path)
        elif campaign._symlink_latest:
            symlink = str(csv_output_path).rsplit("_", 3)[0]
            symlink_path = pathlib.Path(symlink + "_latest.csv")
            if symlink_path.exists(follow_symlinks=False):
                os.remove(symlink_path)
            os.symlink(csv_output_path, symlink_path, False)

        campaign._benchmark.check_dependencies()
        campaign._benchmark.run(
            other_campaigns_seconds=other_campaigns_seconds,
            barrier=barrier,
            continuing=campaign._continuing,
        )
        campaign._move_cmd_file()
