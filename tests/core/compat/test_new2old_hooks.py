# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict

from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.execfn import ExecOutput
from benchkit.core.compat.new2old import CampaignCartesianProduct
from benchkit.utils.dir import get_benches_dir

_SRC_DIR = (get_benches_dir(parent_dir=None) / "tmp_hooks_test").resolve()
_PRE_MARK = _SRC_DIR / "PRE_RAN"
_POST_MARK = _SRC_DIR / "POST_RAN"


class HooksBench:
    def fetch(self, ctx) -> FetchResult:
        src = Path(_SRC_DIR)
        src.mkdir(parents=True, exist_ok=True)
        # reset markers (so reruns are deterministic)
        if _PRE_MARK.exists():
            _PRE_MARK.unlink()
        if _POST_MARK.exists():
            _POST_MARK.unlink()
        return FetchResult(src_dir=src)

    def build(self, ctx) -> BuildResult:
        src = Path(ctx.fetch_result.src_dir)

        (src / "main.c").write_text(
            r"""
#include <stdio.h>
int main() { puts("HELLO"); return 0; }
""".lstrip()
        )

        ctx.exec(argv=["gcc", "-O2", "-o", str(src / "prog"), str(src / "main.c")])
        return BuildResult(build_dir=src)

    def run(self, ctx) -> RunResult:
        build = Path(ctx.build_result.build_dir)
        out: ExecOutput = ctx.exec(argv=[str(build / "prog")], cwd=build)
        return RunResult(outputs=[out])

    def collect(self, ctx) -> Dict[str, Any]:
        # Verify hook markers were created by the legacy engine
        return {
            "stdout": ctx.run_result.outputs[-1].stdout.strip(),
            "pre_hook_ran": _PRE_MARK.is_file(),
            "post_hook_ran": _POST_MARK.is_file(),
        }


class PreMarkHook:
    def __call__(self, *args, **kwargs) -> None:
        _PRE_MARK.write_text("pre\n")


class PostMarkHook:
    def __call__(self, *args, **kwargs) -> None:
        _POST_MARK.write_text("post\n")


def main() -> None:
    parameter_space: dict[str, list[Any]] = {
        # no parameters needed; we just want one run
    }

    bench = HooksBench()

    campaign = CampaignCartesianProduct(
        benchmark=bench,
        parameter_space=parameter_space,
        pre_run_hooks=[PreMarkHook()],
        post_run_hooks=[PostMarkHook()],
        duration_s=1,
    )

    campaign.run()


if __name__ == "__main__":
    main()
