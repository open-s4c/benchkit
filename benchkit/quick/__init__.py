# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import argparse
import shlex
from pathlib import Path
from typing import Any, Dict, List, Tuple

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


def quick_cmd_campaign(
    name: str,
    option_space: Dict[str, List[Any]],
    make_benchmark,
    nb_runs: int = 1,
) -> CampaignCartesianProduct:
    campaign = CampaignCartesianProduct(
        name=name,
        benchmark=_Benchmark(command_fun=make_benchmark),
        nb_runs=nb_runs,
        variables=option_space,
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    return campaign


def parse_cli_optspace(
    option_space: Dict[str, List[Any]],
    cli_args,
) -> Tuple[Dict[str, List[Any]], int]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nb-runs", type=int, default=1)

    # Add CLI args dynamically based on keys in option_space
    for key in option_space.keys():
        parser.add_argument(f"--{key}", type=str)

    args = parser.parse_args(cli_args)

    # Build filtered option_space
    filtered = {}
    for k in option_space:
        cli_val = getattr(args, k)
        if cli_val is not None:
            filtered[k] = [cli_val]
        else:
            filtered[k] = option_space[k]

    nb_runs = args.nb_runs

    return filtered, nb_runs
