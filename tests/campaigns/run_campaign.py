#!/usr/bin/env python3

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
        return ["run_false"]

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
        run_false: bool,
        **kwargs,
    ) -> str:
        current_dir = self.bench_src_path
        environment = self._preload_env(
            run_false=run_false,
            **kwargs,
        )

        run_command = ["/usr/bin/false"] if run_false else ["/usr/bin/true"]
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            run_false=run_false,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=current_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
            ignore_ret_codes=(1,),
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
                "run_false": False,
            },
            {
                "run_false": True,
            },
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
