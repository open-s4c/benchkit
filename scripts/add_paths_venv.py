#!/usr/bin/python3
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


def get_benchkit_path() -> Path:
    this_script = Path(__file__)
    script_dir = this_script.parent
    benchkit_dir = script_dir.parent
    result = benchkit_dir.resolve()
    return result


def main() -> None:
    target_filename = "benchkit-dep.pth"
    dep_filepath = Path("./dependency-paths.txt").resolve()
    venv_path = Path(sys.argv[1] if len(sys.argv) >= 2 else "venv")

    if not venv_path.is_dir():
        print(f"No venv directory found in: {venv_path}", file=sys.stderr)
        exit(1)

    venv_site_packages_path = next(Path(venv_path / "lib").glob("**/site-packages/")).resolve()

    venv_abs_paths = [get_benchkit_path()]

    if dep_filepath.is_file():
        with open(dep_filepath) as dependency_types_file:
            lines = [sline for line in dependency_types_file.readlines() if (sline := line.strip())]
        for line in lines:
            line_path = Path(line)
            if line_path.is_dir():
                venv_abs_path = line_path.resolve()
                venv_abs_paths.append(venv_abs_path)
            else:
                print(f"[WARNING] '{line_path}' is not a directory, skipping.", file=sys.stderr)

    venv_abs_paths = list(dict.fromkeys(venv_abs_paths))  # remove duplicates

    target_path = venv_site_packages_path / target_filename
    with open(target_path, "w") as file:
        file.writelines(f"{p}\n" for p in venv_abs_paths)


if __name__ == "__main__":
    main()
