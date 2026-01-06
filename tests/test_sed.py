# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.core.bktypes.contexts import FetchContext
from benchkit.utils.fetchtools import sed_edit
from benchkit.utils.logging import bkprint, configure_logging


def main() -> None:
    configure_logging(
        rich=True,
        level=logging.DEBUG,
        stdout_level=logging.INFO,
        file_level=logging.DEBUG,
    )

    # Prepare test directory
    benchkit_home_dir = Path("~/.benchkit/").expanduser().resolve()
    test_dir = benchkit_home_dir / "tests" / "sed"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create a test file
    test_file = test_dir / "example.txt"
    test_file.write_text("host=example.com\nport=1234\n")

    ctx = FetchContext(fetch_args={})

    # Apply sed edit
    sed_edit(
        ctx=ctx,
        base_dir=test_dir,
        edits=[
            ("s/host=[^ ]*/host=localhost/", Path("example.txt")),
        ],
    )

    # Read back and verify
    content = test_file.read_text()
    bkprint("File content after sed:")
    bkprint(content)

    assert "host=localhost" in content
    assert "host=example.com" not in content

    bkprint("sed_edit test passed ✔")


if __name__ == "__main__":
    main()
