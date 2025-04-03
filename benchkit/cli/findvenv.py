# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import subprocess
import sys
from pathlib import Path
from typing import List


def create_venv(
    venv_dir: Path,
) -> None:
    venv_parent = str(venv_dir.parent)
    venv_stem = venv_dir.stem

    subprocess.check_output(
        ["/usr/bin/python3", "-m", "venv", f"{venv_stem}"],
        cwd=venv_parent,
        env={},
    )


def install_pkgs_in_venv(
    full: bool,
    latest_deps: bool,
    venv_dir: Path,
    benchkit_repo_path: str,
) -> None:
    pip3 = (venv_dir / "bin/pip3").resolve()

    def install_pip_pkg(packages: List[str]) -> None:
        for pkg in packages:
            print(f"Installing package in venv '{venv_dir}': {pkg}", file=sys.stderr)
        subprocess.check_call([f"{pip3}", "install", "--upgrade"] + packages)

    if full:
        install_pip_pkg(packages=["pip"])
        install_pip_pkg(packages=["setuptools"])
        install_pip_pkg(packages=["wheel"])

    if benchkit_repo_path:
        subprocess.check_call([f"{pip3}", "install", "--editable", f"{benchkit_repo_path}"])
    else:
        install_pip_pkg(packages=["pybenchkit"])

    if full:
        packages = [
            "black<=24.10.0",
            "black[d]<=24.10.0",
            "black[jupyter]<=24.10.0",
            "docopt<=0.6.2",
            "flake8<=7.1.1",
            "isort<=5.13.2",
            "libtmux<=0.40.0",
            "pycodestyle<=2.12.1",
            "pylint<=3.3.2",
        ]
        if latest_deps:
            packages = [p.split("<=")[0].strip() for p in packages]
        install_pip_pkg(packages=packages)


def find_venv(
    full: bool = True,
    latest_deps: bool = True,
    expected_path: str = "",
    benchkit_repo_path: str = "",
) -> Path:
    venv_str = expected_path or ".venv"
    venv_dir = Path(venv_str).resolve()

    python3 = (venv_dir / "bin/python3").resolve()

    if not all([venv_dir.is_dir(), python3.is_file()]):
        print("Warning: venv not found, creating one.", file=sys.stderr)
        create_venv(venv_dir=venv_dir)
        install_pkgs_in_venv(
            full=full,
            latest_deps=latest_deps,
            venv_dir=venv_dir,
            benchkit_repo_path=benchkit_repo_path,
        )

    return venv_dir


def find_global_venv(
    benchkit_repo_path: str = "",
) -> Path:
    if benchkit_repo_path:
        benchkit_repo_path = str(Path(benchkit_repo_path).expanduser().resolve())
    else:
        benchkit_repo_path = ""

    benchkit_global_path = Path("~/.benchkit").expanduser().resolve()
    benchkit_global_path.mkdir(parents=True, exist_ok=True)
    venv_path = benchkit_global_path / ".venv"
    return find_venv(
        full=True,
        latest_deps=False,
        expected_path=str(venv_path),
        benchkit_repo_path=benchkit_repo_path,
    )
