# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Random real-time task-set generation (UUniFast-Discard).
"""

import math
import random
from typing import Any, Dict, List


def uunifast_discard(
    nb_tasks: int,
    total_utilization: float,
    rng: random.Random,
) -> List[float]:
    """
    Draw per-task utilizations summing to `total_utilization`, uniformly over
    the valid simplex, discarding draws where a task exceeds utilization 1
    (Davis & Burns, 2009).

    Args:
        nb_tasks (int): number of tasks.
        total_utilization (float): target total utilization.
        rng (random.Random): seeded random generator, for reproducibility.

    Returns:
        List[float]: the per-task utilizations.
    """
    while True:
        utilizations = []
        remaining = total_utilization
        for i in range(1, nb_tasks):
            next_remaining = remaining * rng.random() ** (1.0 / (nb_tasks - i))
            utilizations.append(remaining - next_remaining)
            remaining = next_remaining
        utilizations.append(remaining)
        if all(u <= 1.0 for u in utilizations):
            return utilizations


def generate_taskset(
    nb_tasks: int,
    total_utilization: float,
    seed: int,
    period_min_us: float = 1_000.0,
    period_max_us: float = 100_000.0,
) -> List[Dict[str, Any]]:
    """
    Generate an implicit-deadline periodic task set: UUniFast-Discard
    utilizations, log-uniform periods, and WCET = utilization x period.

    Args:
        nb_tasks (int): number of tasks.
        total_utilization (float): target total utilization.
        seed (int): seed making the task set reproducible from the record.
        period_min_us (float): lower bound of the period range, in us.
        period_max_us (float): upper bound of the period range, in us.

    Returns:
        List[Dict[str, Any]]: one dict per task (period_us, wcet_us, utilization).
    """
    rng = random.Random(seed)
    utilizations = uunifast_discard(
        nb_tasks=nb_tasks,
        total_utilization=total_utilization,
        rng=rng,
    )
    log_min, log_max = math.log(period_min_us), math.log(period_max_us)
    taskset = []
    for utilization in utilizations:
        period_us = math.exp(rng.uniform(log_min, log_max))
        taskset.append(
            {
                "period_us": period_us,
                "wcet_us": utilization * period_us,
                "utilization": utilization,
            }
        )
    return taskset
