# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict, Tuple

from benchkit.benchmark import CommandWrapper
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.execfn import ExecOutput
from benchkit.core.compat.new2old import CampaignCartesianProduct
from benchkit.utils.dir import get_benches_dir

_SRC_DIR = (get_benches_dir(parent_dir=None) / "tmp_wrapper_test").resolve()


class WrapperBench:
    def fetch(self, ctx) -> FetchResult:
        src = Path(_SRC_DIR)
        src.mkdir(parents=True, exist_ok=True)
        return FetchResult(src_dir=src)

    def build(self, ctx) -> BuildResult:
        src = Path(ctx.fetch_result.src_dir)

        # program: prints WRAP_TAG if set, else prints NONE
        (src / "main.c").write_text(
            r"""
#include <stdio.h>
#include <stdlib.h>

int main() {
    const char* v = getenv("WRAP_TAG");
    if (v) puts(v);
    else puts("NONE");
    return 0;
}
""".lstrip()
        )

        ctx.exec(argv=["gcc", "-O2", "-o", str(src / "prog"), str(src / "main.c")])
        return BuildResult(build_dir=src)

    def run(self, ctx) -> RunResult:
        build = Path(ctx.build_result.build_dir)
        out: ExecOutput = ctx.exec(argv=[str(build / "prog")], cwd=build)
        return RunResult(outputs=[out])

    def collect(self, ctx) -> Dict[str, Any]:
        stdout = ctx.run_result.outputs[-1].stdout.strip()
        return {"stdout": stdout}


class EnvVarWrapper(CommandWrapper):
    """
    Minimal legacy CommandWrapper that injects an environment variable.
    """

    def wrap(
        self,
        command,
        environment,
        wrap_enabled: bool,
        **kwargs,
    ) -> Tuple[list[str], dict[str, str] | None]:
        if not wrap_enabled:
            return list(command), environment

        env = dict(environment or {})
        env["WRAP_TAG"] = "WRAPPED"
        return list(command), env


def main() -> None:
    parameter_space = {
        "wrap_enabled": [True, False],
    }

    bench = WrapperBench()
    wrapper = EnvVarWrapper()

    campaign = CampaignCartesianProduct(
        benchmark=bench,
        parameter_space=parameter_space,
        command_wrappers=[wrapper],
        duration_s=1,
    )

    campaign.run()


if __name__ == "__main__":
    main()
