# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import shlex

from benchkit.utils.dir import caller_dir

_TEMPLATES_DIR = (caller_dir() / "templates").resolve()
_BENCHMARK_BODY_TEMPLATE_PATH = (_TEMPLATES_DIR / "benchmark_body").resolve()
_BENCHMARK_HEADER_TEMPLATE_PATH = (_TEMPLATES_DIR / "benchmark_header").resolve()
_CAMPAIGN_BODY_TEMPLATE_PATH = (_TEMPLATES_DIR / "campaign_body").resolve()
_CAMPAIGN_HEADER_TEMPLATE_PATH = (_TEMPLATES_DIR / "campaign_header").resolve()
_GITIGNORE_TEMPLATE_PATH = (_TEMPLATES_DIR / "gitignore").resolve()


assert _TEMPLATES_DIR.is_dir()
assert _BENCHMARK_BODY_TEMPLATE_PATH.is_file()
assert _BENCHMARK_HEADER_TEMPLATE_PATH.is_file()
assert _CAMPAIGN_BODY_TEMPLATE_PATH.is_file()
assert _CAMPAIGN_HEADER_TEMPLATE_PATH.is_file()
assert _GITIGNORE_TEMPLATE_PATH.is_file()


def generate_benchmark(
    build_command: str,
    run_command: str,
    command_dir: str,
    header: bool,
) -> str:
    build_command_list = shlex.split(build_command) if build_command else []
    run_command_list = shlex.split(run_command) if run_command else ["echo", "PUT-COMMAND-HERE"]
    command_dir_str = str(command_dir) or "."

    template = _BENCHMARK_BODY_TEMPLATE_PATH.read_text()
    benchmark_content = template.format(
        build_command=build_command_list,
        run_command=run_command_list,
        command_dir=command_dir_str,
    )

    if header:
        benchmark_header = _BENCHMARK_HEADER_TEMPLATE_PATH.read_text().strip()
        benchmark_content = benchmark_header + "\n\n" + benchmark_content

    return benchmark_content.strip()


def generate_campaign(
    benchmark_content: str,
    nb_runs: int,
) -> str:
    benchmark_content = benchmark_content or _CAMPAIGN_HEADER_TEMPLATE_PATH.read_text()
    template = _CAMPAIGN_BODY_TEMPLATE_PATH.read_text()
    campaign_content = template.format(
        benchmark_content=benchmark_content,
        nb_runs=nb_runs,
    )

    return campaign_content.strip()


def get_gitignore_content() -> str:
    return _GITIGNORE_TEMPLATE_PATH.read_text().strip() + "\n"
