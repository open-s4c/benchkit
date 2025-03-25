# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import shlex
from pathlib import Path
from typing import Any, Dict, List

from benchkit.benchmark import Benchmark, RecordResult
from benchkit.campaign import CampaignCartesianProduct
from benchkit.utils.misc import TimeMeasure
from benchkit.utils.types import PathType


class _Benchmark(Benchmark):
    def __init__(
        self,
        command_fun,
    ) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=(),
        )

        self._command_fun = command_fun
        self._last_duration_seconds = 0

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        pass

    def single_run(
        self,
        **kwargs,
    ) -> str:
        environment = self._preload_env(
            **kwargs,
        )

        all_args = {}
        all_args |= kwargs
        all_args |= kwargs.get("constants", {})
        all_args |= kwargs.get("constantss", {})
        all_args |= kwargs.get("build_variables", {})
        all_args |= kwargs.get("run_variables", {})
        all_args |= kwargs.get("other_variables", {})

        run_command = self._command_fun(all_args)

        shlexed_run_command = shlex.split(run_command)

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=shlexed_run_command,
            environment=environment,
            **kwargs,
        )

        with TimeMeasure() as run_duration:
            output = self.run_bench_command(
                run_command=run_command,
                wrapped_run_command=wrapped_run_command,
                current_dir=None,
                environment=environment,
                wrapped_environment=wrapped_environment,
                print_output=False,
            )
        self._last_duration_seconds = run_duration.duration_seconds

        if "record_data_dir" in kwargs:
            self._write_to_record_data_dir(
                file_content=output,
                filename="stdout",
                record_data_dir=kwargs["record_data_dir"],
            )

        return output

    def parse_output_to_results(
        self,
        command_output: str,
        build_variables: Dict[str, Any],
        run_variables: Dict[str, Any],
        benchmark_duration_seconds: int,
        record_data_dir: PathType,
        **kwargs,
    ) -> RecordResult:
        return {
            "duration_seconds": self._last_duration_seconds,
        }

    @property
    def bench_src_path(self) -> Path:
        return Path(".").resolve()

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return []

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []


def quick_cmd_evaluate(
    name: str,
    option_space: Dict[str, List[Any]],
    make_benchmark,
) -> None:
    campaign = CampaignCartesianProduct(
        name=name,
        benchmark=_Benchmark(command_fun=make_benchmark),
        nb_runs=1,
        variables=option_space,
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    campaign.run()
