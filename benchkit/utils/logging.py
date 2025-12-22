# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Logging utilities for benchkit.

Goals:
- Provide a consistent, pythonic logging interface across benchkit.
- Avoid global side effects unless the user explicitly configures logging.
- Make it easy for engine/executor/benchmarks to log with a shared convention.

Design:
- configure_logging(): one-time setup helper for handlers/levels/format.
- get_logger(): returns a namespaced logger, eg "benchkit.engine.runonce".

Notes:
- Rich logging is optional and opt-in.
- No global monkey-patching.
- Safe for libraries and CI usage.
"""

import logging
import pprint
import sys
from pathlib import Path
from typing import Any

from rich.logging import RichHandler

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


class LevelColorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.ERROR:
            record.msg = f"[bold red]{record.msg}[/bold red]"
        elif record.levelno >= logging.WARNING:
            record.msg = f"[yellow]{record.msg}[/yellow]"
        return True


def configure_logging(
    *,
    level: int = logging.DEBUG,
    force: bool = False,
    rich: bool = False,
    stdout_level: int | None = logging.INFO,
    file: Path | None = Path("/tmp/benchkit/benchkit.log"),
    file_level: int | None = logging.DEBUG,
) -> None:
    """
    Configure the root "benchkit" logger.

    Args:
        level: Logger level (upper bound).
        force: Remove existing handlers first.
        rich: Use RichHandler on stdout.
        stdout_level: Level for stdout handler.
        file: Optional path to a log file.
        file_level: Level for file handler.
    """
    logger = logging.getLogger("benchkit")
    logger.setLevel(level)

    if force:
        for h in list(logger.handlers):
            logger.removeHandler(h)

    if logger.handlers:
        return

    # ---- Stdout handler ----
    stdout_level = stdout_level or level

    if rich:
        stdout_handler = RichHandler(
            level=stdout_level,
            rich_tracebacks=True,
            markup=True,
            show_path=True,
            show_time=True,
            show_level=True,
        )
        stdout_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
        stdout_handler.addFilter(LevelColorFilter())
    else:
        stdout_handler = logging.StreamHandler(sys.stderr)
        stdout_handler.setLevel(stdout_level)
        stdout_handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, _DEFAULT_DATEFMT))

    logger.addHandler(stdout_handler)

    # ---- File handler ----
    if file is not None:
        file_level = file_level or level
        file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(file, encoding="utf-8")
        file_handler.setLevel(file_level)
        file_handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, _DEFAULT_DATEFMT))
        logger.addHandler(file_handler)

    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger under the "benchkit" namespace.

    Args:
        name: Dotted name suffix, eg "engine.runonce".

    Returns:
        A logger named "benchkit.<name>".
    """
    full = name if name.startswith("benchkit.") else f"benchkit.{name}"
    return logging.getLogger(full)


def bkprint(msg: str, *, logger: str = "ui", level: str = "info") -> None:
    log = get_logger(logger)
    getattr(log, level)(msg)


def bkpprint(
    obj: Any,
    *,
    logger: str = "ui",
    level: str = "info",
    width: int = 80,
    compact: bool = False,
) -> None:
    """
    Pretty-print an object via logging instead of stdout.

    Equivalent to pprint(), but safe with Rich/progress bars.
    """
    log = get_logger(logger)
    text = pprint.pformat(obj, width=width, compact=compact)
    getattr(log, level)(text)
