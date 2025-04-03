#!/usr/bin/python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Install venv in the current directory.
"""
import os
from pathlib import Path

VENV_NAME = "zenv"

if __name__ == "__main__":
    this_dir = Path(__file__).resolve().parent
    benchkit_repo_dir = this_dir.parent
    os.environ["PATH"] += f";{benchkit_repo_dir}"

    from benchkit.cli.pathsvenv import find_venv
    find_venv(
        full=True,
        latest_deps=False,
        expected_path=VENV_NAME,
        benchkit_repo_path=benchkit_repo_dir,
    )
