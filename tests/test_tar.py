# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.core.bktypes.callresults import FetchResult
from benchkit.core.bktypes.contexts import FetchContext
from benchkit.utils.fetchtools import curl, tar_extract
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

    archive = curl(
        ctx=ctx,
        url="https://dbmx.net/kyotocabinet/pkg/kyotocabinet-1.2.76.tar.gz",
        parent_dir=deps_dir,
        name="kyotocabinet-1.2.76.tar.gz",
    )

    src_dir = tar_extract(
        ctx=ctx,
        archive=archive,
    )

    bkprint(str(FetchResult(src_dir=src_dir).src_dir))


if __name__ == "__main__":
    main()
