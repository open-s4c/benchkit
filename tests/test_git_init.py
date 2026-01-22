# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.core.bktypes.callresults import FetchResult
from benchkit.core.bktypes.contexts import FetchContext
from benchkit.utils.fetchtools import git_init
from benchkit.utils.logging import bkprint, configure_logging


def main() -> None:

    configure_logging(
        rich=True,
        level=logging.DEBUG,
        stdout_level=logging.INFO,
        file_level=logging.DEBUG,
    )

    benchkit_home_dir = Path("~/.benchkit/").expanduser().resolve()
    deps_dir = benchkit_home_dir / "tests"

    ctx = FetchContext(fetch_args={})

    repo_dir = deps_dir / "git_init_test_repo"

    repo_dir = git_init(
        ctx=ctx,
        repo_dir=repo_dir,
        initial_branch="main",
    )

    bkprint(str(FetchResult(src_dir=repo_dir).src_dir))


if __name__ == "__main__":
    main()
