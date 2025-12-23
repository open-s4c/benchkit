# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Execution backends for benchkit engines.

An executor is responsible for mechanics:
- calling the benchmark step function
- logging around the call
- (later) concurrency / remote execution / isolation

The engine owns orchestration and semantics.
"""

from dataclasses import dataclass
from typing import Callable, Protocol, TypeVar

from benchkit.platforms import Platform, get_current_platform
from benchkit.utils.logging import get_logger

T = TypeVar("T")


class Executor(Protocol):
    """
    Protocol for an execution backend.

    The callable passed in is a step invocation already bound with
    its context and arguments (typically via ctx.call or explicit call).
    """

    def execute_step(self, *, name: str, fn: Callable[[], T]) -> T: ...


@dataclass(frozen=True)
class LocalExecutor:
    """
    Single-threaded executor that runs steps on the current thread.
    """

    platform: Platform = get_current_platform()

    def execute_step(self, *, name: str, fn: Callable[[], T]) -> T:
        log = get_logger("engine.executor")
        log.info("step.start name=%s", name)
        try:
            out = fn()
        except Exception:
            log.exception("step.fail name=%s", name)
            raise
        log.info("step.done name=%s", name)
        return out
