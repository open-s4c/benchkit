# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict

from benchkit.commandwrappers.taskset import TasksetWrap
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.execfn import ExecOutput
from benchkit.core.compat.new2old import CampaignCartesianProduct
from benchkit.utils.dir import get_benches_dir

_SRC_DIR = (get_benches_dir(parent_dir=None) / "tmp_tasksetwrap_test").resolve()


class TasksetWrapBench:
    def fetch(self, ctx) -> FetchResult:
        src = Path(_SRC_DIR)
        src.mkdir(parents=True, exist_ok=True)
        return FetchResult(src_dir=src)

    def build(self, ctx) -> BuildResult:
        src = Path(ctx.fetch_result.src_dir)

        (src / "main.c").write_text(
            r"""
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>

static int count_set(const cpu_set_t* set) {
    int c = 0;
    for (int i = 0; i < CPU_SETSIZE; i++) {
        if (CPU_ISSET(i, set)) c++;
    }
    return c;
}

static int first_set(const cpu_set_t* set) {
    for (int i = 0; i < CPU_SETSIZE; i++) {
        if (CPU_ISSET(i, set)) return i;
    }
    return -1;
}

int main() {
    cpu_set_t set;
    CPU_ZERO(&set);
    if (sched_getaffinity(0, sizeof(set), &set) != 0) {
        perror("sched_getaffinity");
        return 2;
    }
    int n = count_set(&set);
    int first = first_set(&set);
    printf("AFFINITY_COUNT=%d\n", n);
    printf("AFFINITY_FIRST=%d\n", first);
    return 0;
}
""".lstrip()
        )

        # Build (assumes gcc + glibc headers)
        ctx.exec(argv=["gcc", "-O2", "-o", str(src / "prog"), str(src / "main.c")])
        return BuildResult(build_dir=src)

    def run(self, ctx) -> RunResult:
        build = Path(ctx.build_result.build_dir)
        out: ExecOutput = ctx.exec(argv=[str(build / "prog")], cwd=build)
        return RunResult(outputs=[out])

    def collect(self, ctx) -> Dict[str, Any]:
        stdout = ctx.run_result.outputs[-1].stdout.strip().splitlines()
        kv = {}
        for line in stdout:
            if "=" in line:
                k, v = line.split("=", 1)
                kv[k.strip()] = v.strip()
        return {
            "affinity_count": int(kv.get("AFFINITY_COUNT", "-1")),
            "affinity_first": int(kv.get("AFFINITY_FIRST", "-1")),
            "raw_stdout": "\n".join(stdout),
        }


def main() -> None:
    parameter_space = {
        "master_thread_core": [None, 0, 1],
    }

    bench = TasksetWrapBench()
    wrapper = TasksetWrap()

    campaign = CampaignCartesianProduct(
        benchmark=bench,
        parameter_space=parameter_space,
        command_wrappers=[wrapper],
        duration_s=1,
    )

    campaign.run()


if __name__ == "__main__":
    main()
