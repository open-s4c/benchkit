# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.core.bktypes.callresults import RunResult
from benchkit.core.bktypes.contexts import RunContext


class DDBench:
    """
    DD benchmark (benchkit core protocol).

    CPU-intensive workload using dd to read from /dev/urandom and write to
    /dev/null.  Useful for testing perf-based profiling (e.g. flamegraphs)
    because it generates measurable CPU activity, unlike sleep.

    - run: execute dd if=/dev/urandom of=/dev/null bs=1M count=block_count
    """

    def run(
        self,
        ctx: RunContext,
        block_count: int,
    ) -> RunResult:
        out = ctx.exec(
            argv=[
                "dd",
                "if=/dev/urandom",
                "of=/dev/null",
                "bs=1M",
                f"count={block_count}",
            ],
            cwd=ctx.build_result.build_dir if ctx.build_result is not None else None,
            print_output=False,
            ignore_ret_codes=(1,),
        )
        return RunResult(outputs=[out])
