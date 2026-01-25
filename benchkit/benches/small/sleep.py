# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.core.bktypes.callresults import RunResult
from benchkit.core.bktypes.contexts import RunContext


class SleepBench:
    """
    Sleep benchmark (benchkit core protocol).

    - run: execute /usr/bin/sleep for duration_seconds
    """

    def run(
        self,
        ctx: RunContext,
        duration_seconds: int,
    ) -> RunResult:
        out = ctx.exec(
            argv=["/usr/bin/sleep", f"{duration_seconds}s"],
            cwd=ctx.build_result.build_dir if ctx.build_result is not None else None,
            print_output=False,
            ignore_ret_codes=(1,),
            output_is_log=True,
        )
        return RunResult(outputs=[out])
