#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
from typing import Any, Dict, Iterable, List

from benchkit.benchmark import Benchmark
from benchkit.campaign import CampaignIterateVariables, CampaignSuite
from benchkit.utils.dir import caller_dir


class SimpleBenchmark(Benchmark):
    def __init__(
        self,
    ) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=(),
        )

    @property
    def bench_src_path(self) -> pathlib.Path:
        return caller_dir()

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return ["ignored_codes"]

    def clean_bench(self) -> None:
        pass

    def prebuild_bench(
        self,
        **kwargs,
    ) -> int:
        return 0

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        pass

    def single_run(
        self,
        ignored_codes: Iterable[int],
        **kwargs,
    ) -> str:
        current_dir = self.bench_src_path
        environment = self._preload_env(
            ignored_codes=ignored_codes,
            **kwargs,
        )

        run_command = ["/usr/bin/false"]
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            ignored_codes=ignored_codes,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=current_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}
        return result_dict


def main() -> None:
    campaign = CampaignIterateVariables(
        name="simple",
        benchmark=SimpleBenchmark(),
        nb_runs=1,
        variables=[
            {
                "ignored_codes": (1, 3),
            }
        ],
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
    )

    campaign_suite = CampaignSuite(campaigns=[campaign])

    campaign_suite.run_suite()


if __name__ == "__main__":
    main()
