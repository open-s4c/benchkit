# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict, Tuple

from benchkit.benchmark import SharedLib as SharedLibOld
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.execfn import ExecOutput
from benchkit.core.compat.new2old import CampaignCartesianProduct
from benchkit.utils.dir import get_benches_dir
from benchkit.utils.types import EnvironmentVariables, LdPreloadLibraries

_SRC_DIR = (get_benches_dir(parent_dir=None) / "tmp_preload_test").resolve()


class PreloadBench:
    def fetch(self, ctx) -> FetchResult:
        src = Path(_SRC_DIR)
        src.mkdir(parents=True, exist_ok=True)
        return FetchResult(src_dir=src)

    def build(self, ctx) -> BuildResult:
        src = Path(ctx.fetch_result.src_dir)

        # program: calls puts("hello")
        (src / "main.c").write_text(
            r"""
#include <stdio.h>
int main() { puts("hello"); return 0; }
""".lstrip()
        )

        # preload library: overrides puts
        (src / "hook.c").write_text(
            r"""
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>

typedef int (*puts_t)(const char *);

int puts(const char *s) {
    puts_t real_puts = (puts_t)dlsym(RTLD_NEXT, "puts");
    real_puts("HOOKED");
    return real_puts(s);
}
""".lstrip()
        )

        # Build both (assumes gcc is available)
        ctx.exec(
            argv=[
                "gcc",
                "-O2",
                "-fPIC",
                "-shared",
                "-o",
                str(src / "libhook.so"),
                str(src / "hook.c"),
                "-ldl",
            ]
        )
        ctx.exec(argv=["gcc", "-O2", "-o", str(src / "prog"), str(src / "main.c")])

        # Minimal BuildResult shape: provide build_dir
        return BuildResult(build_dir=src)

    def run(self, ctx) -> RunResult:
        build = Path(ctx.build_result.build_dir)
        out: ExecOutput = ctx.exec(argv=[str(build / "prog")], cwd=build)

        return RunResult(outputs=[out])

    def collect(self, ctx) -> Dict[str, Any]:
        stdout = ctx.run_result.outputs[-1].stdout
        parsed_out = stdout.strip().replace("\n", "-")
        return {"stdout": parsed_out}


# --- tiny legacy SharedLib ---------------------------------------------------


class HookSharedLib(SharedLibOld):
    def preload(
        self,
        hook_enabled: bool,
        other_variables: dict[str, Any],
        **kwargs,
    ) -> Tuple[LdPreloadLibraries, EnvironmentVariables]:
        build_dir = _SRC_DIR

        if not hook_enabled:
            return [], {}

        # In our new protocol build, build_dir == src_dir and contains libhook.so
        lib = build_dir / "libhook.so"
        assert lib.is_file()
        return [lib], {}  # let compat construct LD_PRELOAD


def main() -> None:
    parameter_space = {
        "hook_enabled": [True, False],
    }

    bench = PreloadBench()
    lib = HookSharedLib()

    campaign = CampaignCartesianProduct(
        benchmark=bench,
        parameter_space=parameter_space,
        shared_libs=[lib],
        duration_s=1,
    )

    campaign.run()


if __name__ == "__main__":
    main()
