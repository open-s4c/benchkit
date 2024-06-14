#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import sys
from datetime import datetime
from typing import Generator

this_year = datetime.now().year

copyright_line_template = "# Copyright (C) {year} {name} All rights reserved."
spdx_line = "# SPDX-License-Identifier: MIT"


def check_copyright_line(line: str) -> bool:
    year_start = 2023
    try:
        parts = line.split()
        year_index = parts.index("(C)") + 1
        year = int(parts[year_index].strip(","))
        name_parts = parts[year_index + 1 : -3]  # Remove "All rights reserved." from the end
        name = " ".join(name_parts)

        if not (year_start <= year <= this_year):
            return False

        if "huawei" in name.lower() and name != "Huawei Technologies Co., Ltd.":
            return False

        if "brussel" in name.lower() and name != "Vrije Universiteit Brussel.":
            return False

        if line.endswith(". All rights reserved."):
            return True
    except (ValueError, IndexError):
        return False

    return False


def has_valid_header(file_path: str) -> bool:
    lines = []
    try:
        with open(file_path, "r") as file:
            lines.append(next(file).strip())
            lines.append(next(file).strip())
            lines.append(next(file).strip())
    except StopIteration:
        # File has fewer than 3 lines
        pass

    for i, line in enumerate(lines):
        if line.startswith("# Copyright"):
            if check_copyright_line(line):
                if i + 1 < len(lines) and lines[i + 1] == spdx_line:
                    return True
            break

    return False


def find_py_files(start_dir: str) -> Generator[str, None, None]:
    for root, dirs, files in os.walk(start_dir):
        # Exclude venv/ directories
        if "venv" in dirs:
            dirs.remove("venv")
        for file in files:
            if file.endswith(".py"):
                yield os.path.join(root, file)


def main() -> None:
    for file_path in find_py_files("."):
        if not has_valid_header(file_path):
            print(f"{file_path} does not have the valid copyright header", file=sys.stderr)


if __name__ == "__main__":
    main()
