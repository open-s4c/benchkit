# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import subprocess
from pathlib import Path

from benchkit.cli.findvenv import find_global_venv

_BENCHKIT_INSTALL_PATH = Path("~/.benchkit").expanduser().resolve()
COLOR_START = "\033[95m"
COLOR_END = "\033[0m"


def _detect_parent_shell() -> str:
    # Get the command name of the parent process
    output = subprocess.check_output(
        ["ps", "-p", str(os.getppid()), "-o", "comm="],
        text=True,
    ).strip()
    return Path(output).name


def _add_symlinks(venv_path: Path) -> None:
    """Create symlinks in ~/.benchkit for all activate scripts."""
    venv_bin = venv_path / "bin"
    target_dir = _BENCHKIT_INSTALL_PATH

    for activate_file in venv_bin.glob("activate*"):
        link_name = target_dir / activate_file.name
        try:
            if link_name.is_symlink() or link_name.exists():
                link_name.unlink()
            link_name.symlink_to(activate_file)
            print(f"Linked: {link_name} -> {activate_file}")
        except Exception as e:
            print(f"Failed to link {link_name}: {e}")


def benchkit_install(
    editable: bool = False,
    benchkit_repo_path: str = "",
) -> None:
    if editable and not benchkit_repo_path:
        benchkit_parent_path = _BENCHKIT_INSTALL_PATH
        benchkit_parent_path.mkdir(parents=True, exist_ok=True)
        benchkit_repo_path_hidden = benchkit_parent_path / "benchkit"
        if not benchkit_repo_path_hidden.is_dir():
            subprocess.check_call(
                args=["git", "clone", "https://github.com/open-s4c/benchkit.git"],
                cwd=benchkit_parent_path,
            )
        benchkit_repo_path = str(benchkit_repo_path_hidden)

    venv_path = find_global_venv(benchkit_repo_path=benchkit_repo_path)
    _add_symlinks(venv_path=venv_path)
    print(f"{COLOR_START}-- benchkit installed.{COLOR_END}")
    benchkit_activate()


def benchkit_activate() -> None:
    shell = _detect_parent_shell()

    suffix = ""
    if "fish" in shell:
        suffix = ".fish"
    elif "csh" in shell or "tcsh" in shell:
        suffix = ".csh"
    # Default for bash, zsh, etc. is ""

    activate_path = f"~/.benchkit/activate{suffix}"

    print(f"{COLOR_START}-- Activate by running this:\n. {activate_path}{COLOR_END}")


if __name__ == "__main__":
    benchkit_install(
        editable=True,
        benchkit_repo_path="~/git/vub/benchkit",
    )
