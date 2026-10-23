# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.core.bktypes.contexts import FetchContext
from benchkit.utils.fetchtools import iso_extract
from benchkit.utils.logging import configure_logging


def main() -> None:
    configure_logging(
        rich=True,
        level=logging.DEBUG,
        stdout_level=logging.INFO,
        file_level=logging.DEBUG,
    )

    benchkit_home_dir = Path("~/.benchkit/").expanduser().resolve()
    deps_dir = benchkit_home_dir / "deps"
    extract_dir = benchkit_home_dir / "test-iso-extract"

    ctx = FetchContext(fetch_args={})
    iso = deps_dir / "PATH_TO_ISO"

    iso_extract(ctx=ctx, image=iso, destination=extract_dir)
    print(f"Extracted ISO at {extract_dir}")


if __name__ == "__main__":
    main()
