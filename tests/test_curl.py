# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.core.bktypes.callresults import FetchResult
from benchkit.core.bktypes.contexts import FetchContext
from benchkit.utils.fetchtools import curl
from benchkit.utils.logging import bkprint, configure_logging


def main() -> None:

    configure_logging(
        rich=True,
        level=logging.DEBUG,
        stdout_level=logging.INFO,
        file_level=logging.DEBUG,
    )

    benchkit_home_dir = Path("~/.benchkit/").expanduser().resolve()
    deps_dir = benchkit_home_dir / "deps"

    ctx = FetchContext(fetch_args={})

    volano_dir = curl(
        ctx=ctx,
        url="https://www.volano.com/files/volano_benchmark_2_9_0.class",
        parent_dir=deps_dir,
        name="volano_benchmark_2_9_0.class",
    )

    bkprint(str(FetchResult(src_dir=volano_dir).src_dir))


if __name__ == "__main__":
    main()
