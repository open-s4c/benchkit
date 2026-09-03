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

import os
import pathlib
from typing import TYPE_CHECKING, Optional

from benchkit.engine.policies import ExecutionPolicy, SequentialPolicy

if TYPE_CHECKING:
    from benchkit.campaign import Campaign


class ExecutionEngine:
    """
    Own the orchestration of campaign execution.

    This is the Tier-2 entry point of the new API: advanced users compose an
    engine and run campaigns through it. Scheduling is delegated to the
    engine's `ExecutionPolicy` (sequential by default); future slices add
    `generator=` and `store=` here as well.

    Note: while `Campaign` transitions to a pure data structure, the engine
    reads some of its non-public members (benchmark, continuing/symlink
    flags, command-file bookkeeping). This protected access is deliberate
    and temporary: it disappears as those responsibilities migrate to the
    engine and its result store.
    """

    # pylint: disable=protected-access

    def __init__(
        self,
        policy: Optional[ExecutionPolicy] = None,
    ) -> None:
        """
        Args:
            policy (Optional[ExecutionPolicy], optional):
                the scheduling policy executing the campaigns given to this
                engine. Defaults to a `SequentialPolicy`.
        """
        self._policy = policy if policy is not None else SequentialPolicy()

    @property
    def policy(self) -> ExecutionPolicy:
        """
        Return the scheduling policy of this engine.

        Returns:
            ExecutionPolicy: the scheduling policy of this engine.
        """
        return self._policy

    def run(
        self,
        campaign: "Campaign",
        *,
        other_campaigns_seconds: int = 0,
    ) -> None:
        """
        Run a single campaign, possibly among other campaigns in a suite.

        Args:
            campaign (Campaign):
                the campaign to execute.
            other_campaigns_seconds (int, optional):
                time remaining to execute other campaigns in the suite.
                Defaults to 0.
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
        self._policy.execute(
            campaign=campaign,
            other_campaigns_seconds=other_campaigns_seconds,
        )
        campaign._move_cmd_file()
