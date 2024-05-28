#!/usr/bin/env python3
"""
Adds the paths specified in dependency-paths.txt to the benchkit-dep.pth files
in the site-packages directory.
"""
import os
from pathlib import Path

target_file = "benchkit-dep.pth"
venv_site_packages_path = next(Path("venv/lib").glob("**/site-packages/")).resolve()

venv_rel_paths = []
with open("./dependency-paths.txt") as dependency_types_file:
    for line in dependency_types_file:
        line_path = Path(line.rstrip())
        if line_path.is_dir():
            # get the path relative to the site-packages path
            venv_rel_path = line_path.resolve().relative_to(venv_site_packages_path, walk_up=True)
            venv_rel_paths.append(venv_rel_path)

with open(os.path.join(venv_site_packages_path, target_file), "a") as file:
    file.writelines(map(lambda p: str(p) + '\n', venv_rel_paths))

