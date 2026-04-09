# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import subprocess
from pathlib import Path

import black
import isort

from benchkit.cli.generate import generate_benchmark, generate_campaign, get_gitignore_content
from benchkit.utils.misc import get_benchkit_temp_folder_str

_DOTGIT_DIR = Path(".git")
_GITIGNORE_PATH = Path(".gitignore")
_VENV_PATH = Path(".venv")
_CAMPAIGNS_DIR = Path("campaigns")
_BENCHMARKS_DIR = _CAMPAIGNS_DIR / "benchmarks"


def create_git() -> None:
    if _DOTGIT_DIR.is_dir():
        return
    subprocess.run(["git", "init"])


def gitignore() -> None:
    _GITIGNORE_PATH.write_text(get_gitignore_content())


def git_add() -> None:
    subprocess.run(["git", "add", "."])


def git_status() -> None:
    subprocess.run(["git", "status"])


def format_py_src(src_content: str) -> str:
    black_mode = black.Mode(line_length=100)  # TODO apply toml config file
    src_content_isort = isort.code(code=src_content)
    src_content_black = black.format_str(src_contents=src_content_isort, mode=black_mode)
    src_content_result = src_content_black.strip()
    return src_content_result


def benchkit_init(
    build_command: str,
    run_command: str,
    nb_runs: int,
    command_dir: str,
    campaign_filename: str,
    git: bool,
    split_benchmark_campaign: bool,
) -> None:
    campaign_filename = campaign_filename or "campaign.py"

    benchmark_content = generate_benchmark(
        build_command=build_command,
        run_command=run_command,
        command_dir=command_dir,
        header=split_benchmark_campaign,
    )
    campaign_content = generate_campaign(
        benchmark_content="" if split_benchmark_campaign else benchmark_content,
        nb_runs=nb_runs,
    )

    if git:
        create_git()
        gitignore()

    if split_benchmark_campaign:
        campaign_content = format_py_src(campaign_content)
        benchmark_content = format_py_src(benchmark_content)
        _CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
        _BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
        campaign_pathname = (_CAMPAIGNS_DIR / campaign_filename).resolve()
        benchmark_pathname = (_BENCHMARKS_DIR / "__init__.py").resolve()

        if campaign_pathname.is_file():
            print(f"❌ {campaign_pathname} already exists. Aborting.")
            exit(1)

        if benchmark_pathname.is_file():
            print(f"❌ {benchmark_pathname} already exists. Aborting.")
            exit(1)

        campaign_pathname.write_text(campaign_content)
        benchmark_pathname.write_text(benchmark_content)

        rel_benchmark = benchmark_pathname.relative_to(Path.cwd())
        rel_campaign = campaign_pathname.relative_to(Path.cwd())
        print(
            (
                f'✅ Initialized benchmark ("{rel_benchmark}") '
                f'& campaign ("{rel_campaign}")\n'
                f'with command: "{run_command}"'
            )
        )
    else:
        campaign_content = format_py_src(campaign_content)
        campaign_pathname = Path(campaign_filename).resolve()

        if campaign_pathname.is_file():
            print(f"❌ {campaign_pathname} already exists. Aborting.")
            exit(1)

        campaign_pathname.write_text(campaign_content)

        rel_campaign = campaign_pathname.relative_to(Path.cwd())
        print(
            (
                f'✅ Initialized single-file benchmark & campaign: "{rel_campaign}"\n'
                f'   with command: "{run_command}"'
            )
        )

    if git:
        git_add()
        git_status()


if __name__ == "__main__":
    benchkit_init(
        build_command="",
        run_command="echo throughput=10",
        nb_runs=4,
        command_dir=f"{get_benchkit_temp_folder_str()}/c",
        campaign_filename="testcamp.py",
        git=False,
        split_benchmark_campaign=True,
    )
