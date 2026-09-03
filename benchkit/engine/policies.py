# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Execution policies for benchkit campaigns.

An `ExecutionPolicy` decides how the work of a campaign is scheduled:
sequentially, in parallel, as a portfolio, with early stopping, ... The
engine owns the campaign-level bookkeeping and delegates the execution
itself to its policy.

Today the unit of schedulable work is the whole benchmark run: the record
iteration still lives in the legacy `Benchmark.run()` loop, and
`SequentialPolicy` formalizes the current behavior by invoking it once.
When that loop is dismantled, policies will iterate the campaign's
`record_generator` and feed its `result_store` per record; the `execute()`
signature is designed to survive that move unchanged. A policy must not
assume the parameter space is finite: execution ends when the generator is
exhausted, not when a precomputed count is reached.
"""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from benchkit.campaign import Campaign


class ExecutionPolicy(Protocol):
    """
    Protocol describing a scheduling policy for campaign execution.

    Structural typing: any object with a conforming `execute()` method is a
    valid policy; no inheritance is required.
    """

    def execute(
        self,
        campaign: "Campaign",
        *,
        other_campaigns_seconds: int = 0,
    ) -> None:
        """
        Execute the work of the given campaign.

        Args:
            campaign (Campaign):
                the campaign whose benchmark runs are to be scheduled; the
                policy reads what it needs (benchmark, record generator,
                result store) from the campaign's declarative surface.
            other_campaigns_seconds (int, optional):
                time remaining to execute other campaigns in the suite.
                Defaults to 0.
        """
        ...


class SequentialPolicy:
    """
    Execute the campaign's runs one after the other, on the current thread.

    This is the current (and historical) benchkit behavior, formalized as
    the reference policy implementation.
    """

    # pylint: disable=protected-access  # temporary, as in ExecutionEngine

    def execute(
        self,
        campaign: "Campaign",
        *,
        other_campaigns_seconds: int = 0,
    ) -> None:
        """
        Execute all the runs of the campaign sequentially.

        Args:
            campaign (Campaign):
                the campaign whose benchmark runs are to be scheduled.
            other_campaigns_seconds (int, optional):
                time remaining to execute other campaigns in the suite.
                Defaults to 0.
        """
        campaign._benchmark.run(
            other_campaigns_seconds=other_campaigns_seconds,
            continuing=campaign._continuing,
        )
