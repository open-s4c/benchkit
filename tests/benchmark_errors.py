#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.benchmark import Benchmark
from benchkit.utils.types import SplitCommand
from shell.shellasync import AsyncProcess
from typing import Iterable
import subprocess


class TestBench(Benchmark):
    def __init__(self) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=(),
        )

    def single_run(
        self,
        **kwargs,
    ) -> str:
        def run_command(
            command: SplitCommand,
            ignore_any_error_code: bool,
            ignore_ret_codes: Iterable[int]=(),
        ) -> str | AsyncProcess:
            return self.run_bench_command(
                run_command=command,
                wrapped_run_command=command,
                current_dir=".",
                environment={},
                wrapped_environment={},
                print_output=False,
                ignore_ret_codes=ignore_ret_codes,
                ignore_any_error_code=ignore_any_error_code,
            )

        error_raised = False
        try:
            run_command(
                command=["python3", "-c", "exit(3)"],
                ignore_any_error_code=False,
                ignore_ret_codes=[],
            )
        except subprocess.CalledProcessError as e:
            retcode = e.returncode
            if 3 == retcode:
                error_raised = True
        assert error_raised

        error_raised = False
        try:
            run_command(
                command=["python3", "-c", "exit(3)"],
                ignore_any_error_code=False,
                ignore_ret_codes=[1, 2],
            )
        except subprocess.CalledProcessError as e:
            retcode = e.returncode
            if 3 == retcode:
                error_raised = True
        assert error_raised

        run_command(
            command=["python3", "-c", "exit(3)"],
            ignore_any_error_code=False,
            ignore_ret_codes=[3],
        )

        run_command(
            command=["python3", "-c", "exit(3)"],
            ignore_any_error_code=False,
            ignore_ret_codes=[1, 2, 3],
        )

        run_command(
            command=["python3", "-c", "exit(3)"],
            ignore_any_error_code=True,
            ignore_ret_codes=[],
        )

        return ""


def main() -> None:
    bench = TestBench()
    bench.single_run()


if __name__ == "__main__":
    main()
