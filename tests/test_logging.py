# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Example program demonstrating Benchkit logging facilities.

This file is not a unit test but a runnable example showing:
- how to configure logging in Benchkit
- how standard logging integrates with bkprint / bkpprint
- how different log levels are routed to stdout vs file
"""

import logging
from pathlib import Path

from benchkit.utils.logging import (
    bkpprint,
    bkprint,
    configure_logging,
)


def main() -> None:
    # Configure benchkit logging
    configure_logging(
        rich=True,  # Rich handler for stdout
        level=logging.DEBUG,  # Root logger level
        stdout_level=logging.INFO,  # What users see on stdout
        file_level=logging.DEBUG,  # Full verbosity in log file
    )

    logger = logging.getLogger("benchkit.ui")

    # Demonstrate standard logging
    logger.debug("This is a DEBUG message (file only).")
    logger.info("This is an INFO message (stdout + file).")
    logger.warning("This is a WARNING message.")
    logger.error("This is an ERROR message.")

    # Demonstrate bkprint: user-facing, nicely formatted output
    bkprint("Benchkit logging demo started 🚀")

    # Some fake structured data (e.g., benchmark metadata)
    example_result = {
        "benchmark": "example",
        "status": "success",
        "metrics": {
            "latency_ms": [1.2, 1.1, 1.3],
            "throughput_ops": 42_000,
        },
        "paths": {
            "workdir": Path("/tmp/benchkit/work"),
            "results": Path("/tmp/benchkit/results"),
        },
    }

    bkprint("Pretty-printed result object:")
    bkpprint(example_result)

    bkprint(msg="Another warning, using bkprint().", level="warning")
    bkprint(msg="Another error, using bkprint().", level="error")

    # Mixing logging and bkprint intentionally
    logger.info("Example completed successfully.")
    bkprint("All done ✅")


if __name__ == "__main__":
    main()
