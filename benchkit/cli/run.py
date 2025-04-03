# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import subprocess
import sys
from pathlib import Path

from benchkit.cli.findvenv import find_global_venv


def benchkit_run(
    campaign_file: str,
) -> None:
    campaign_path = Path(campaign_file if campaign_file else "campaign.py")

    if not campaign_path.is_file():
        print(f"Campaign file not found: {campaign_path}", file=sys.stderr)
        exit(1)

    venv_path = find_global_venv()
    python3 = venv_path / "bin/python3"

    subprocess.check_call([f"{python3}", f"{campaign_path}"])
