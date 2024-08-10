#!/usr/bin/env python3
"""
Adds the paths specified in dependency-paths.txt to the benchkit-dep.pth files
in the site-packages directory.
"""
import sys
from pathlib import Path


def relative_to(path_to_return: Path, relto_path: Path) -> Path:
    if sys.version_info >= (3, 12):
        result = path_to_return.resolve().relative_to(relto_path, walk_up=True)
    else:
        import os
        result = os.path.relpath(
            os.path.realpath(path_to_return),
            os.path.realpath(relto_path),
        )
    return result


def main() -> None:
    target_filename = "benchkit-dep.pth"
    dep_filepath = Path("./dependency-paths.txt").resolve()
    venv_path = sys.argv[1] if len(sys.argv) >= 2 else "venv"

    venv_site_packages_path = next(Path(f"{venv_path}/lib").glob("**/site-packages/")).resolve()

    venv_rel_paths = []

    if dep_filepath.is_file():
        with open(dep_filepath) as dependency_types_file:
            lines = dependency_types_file.readlines()
        for line in lines:
            line_path = Path(line.rstrip())
            if not line_path.is_dir():
                print(f"[WARNING] {line_path} is not a directory", file=sys.stderr)
                continue
            # get the path relative to the site-packages path
            venv_rel_path = relative_to(path_to_return=line_path.resolve(), relto_path=venv_site_packages_path)
            venv_rel_paths.append(venv_rel_path)

    target_path = venv_site_packages_path / target_filename
    with open(target_path, "a") as file:
        file.writelines(map(lambda p: str(p) + '\n', venv_rel_paths))


if __name__ == "__main__":
    main()
