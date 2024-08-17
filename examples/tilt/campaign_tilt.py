#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Minimal example to run tilt locks.
"""

import pathlib
from typing import Any, Dict, Iterable, List

from tiltlib import TiltLib, cmake_configure_build

from benchkit.benchmark import Benchmark
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite, Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.dir import caller_dir

tilt_locks_dir = caller_dir() / "locks"
vsync_dir = (tilt_locks_dir / "../deps/libvsync/").resolve()


class Bench(Benchmark):
    def __init__(
        self,
        shared_libs: Iterable[SharedLib] = (),
        platform: Platform = None,
    ) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=shared_libs,
            pre_run_hooks=(),
            post_run_hooks=(),
        )
        if platform is not None:
            self.platform = platform
        self._build_dir = self.bench_src_path / f"build-{self.platform.hostname}"

    @property
    def bench_src_path(self) -> pathlib.Path:
        return caller_dir() / "bench"

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return ["lock"]

    def clean_bench(self) -> None:
        pass

    def prebuild_bench(
        self,
        **kwargs,
    ) -> int:
        cmake_configure_build(
            platform=self.platform,
            src_dir=self.bench_src_path,
            build_dir=self._build_dir,
            debug=self.must_debug(),
            make_suffix=self._parallel_make_str(),
        )
        return 0

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        pass

    def single_run(
        self,
        **kwargs,
    ) -> str:
        current_dir = self._build_dir
        environment = self._preload_env(
            **kwargs,
        )

        run_command = ["./mutex"]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
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
        print(output)
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}
        return result_dict


def main() -> None:
    tiltlib = TiltLib(tilt_locks_dir=tilt_locks_dir)
    tiltlib.build()

    campaigns = [
        CampaignCartesianProduct(
            name="tilt",
            benchmark=Bench(shared_libs=[tiltlib]),
            nb_runs=1,
            variables={
                "lock": ["", "taslock", "caslock", "vcaslock-nolse", "vcaslock-lse"],
            },
            constants=None,
            debug=False,
            gdb=False,
            enable_data_dir=True,
            continuing=False,
        ),
    ]
    suite = CampaignSuite(campaigns=campaigns)
    suite.print_durations()
    suite.run_suite()


if __name__ == "__main__":
    main()
