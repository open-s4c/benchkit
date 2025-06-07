#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
from pathlib import Path
from typing import List

# File extensions to consider as "text" files
TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".sh",
    ".toml",
    ".c",
    ".cpp",
    ".h",
    ".in",
    ".rs",
    ".yml",
    ".yaml",
    ".json",
    ".cfg",
    ".ini",
}

# Directories to skip
EXCLUDED_DIRS = {"venv", ".venv"}


def is_text_file(path: Path) -> bool:
    with path.open("rb") as f:
        chunk = f.read(1024)
        # Heuristic: binary files usually contain null bytes
        return b"\0" not in chunk


def is_excluded(path: Path, repo_root: Path) -> bool:
    rel_parts = path.relative_to(repo_root).parts
    return any(part in EXCLUDED_DIRS for part in rel_parts)


def check_final_newline(repo_root: Path) -> List[Path]:
    bad_files = []

    for path in repo_root.rglob("*"):
        if (
            path.is_file()
            and path.suffix in TEXT_EXTENSIONS
            and not is_excluded(path, repo_root)
            and is_text_file(path)
        ):
            if path.stat().st_size == 0:
                continue  # skip empty files
            with path.open("rb") as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":
                    bad_files.append(path)

    return bad_files


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    bad_files = check_final_newline(repo_root)

    if bad_files:
        print("The following files do not end with a newline:")
        for path in bad_files:
            print("  ", path.relative_to(repo_root))
        exit(1)


if __name__ == "__main__":
    main()
