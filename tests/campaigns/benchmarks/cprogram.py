# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.benchmark import Benchmark, CommandWrapper, CommandAttachment, SharedLib, PreRunHook, PostRunHook
from benchkit.platforms import Platform
import pathlib
from typing import Any, Dict, List, Iterable


c_program = """
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>

int main() {
    for (int i = 0; i < 100; i++) {
        printf("Iteration %d\\n", i);
        fflush(stdout);
        usleep(50000 + rand() % 50001);  // Sleep for 50-100 milliseconds
    }
    return 0;
}
"""


class CProgramBench(Benchmark):
    def __init__(
        self,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform

        self._bench_path = pathlib.Path("/tmp/benchkit/cprogram")
        self.platform.comm.makedirs(path=self._bench_path, exist_ok=True)

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return []

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
        self.platform.comm.write_content_to_file(
            content=c_program,
            output_filename=self._bench_path / "cprogram.c",
        )
        self.platform.comm.shell(command="make cprogram", current_dir=self._bench_path)

    def single_run(
        self,
        **kwargs,
    ) -> str:
        current_dir = self.bench_src_path
        environment = self._preload_env(
            **kwargs,
        )

        run_command = ["./cprogram"]

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
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}
        return result_dict
