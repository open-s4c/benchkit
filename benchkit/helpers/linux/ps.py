# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utility functions relying on `ps` utility.
"""

import re
from typing import List

from benchkit.shell.shell import shell_out


def get_threads_of_process(pid: int) -> List[int]:
    """Get thread identifiers (TIDs) of the given process identifier (PID).

    Args:
        pid (int): the PID of the process to query.

    Raises:
        ValueError: if cannot parse `ps` output.

    Returns:
        List[int]: list of threads of the given process.
    """
    ps_output = shell_out(
        f"ps -T -p {pid}",
        print_input=False,
        print_output=False,
    )

    tids = []
    for line in ps_output.splitlines()[1:]:
        m = re.match(
            pattern=r"\s*(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(.*)$",
            string=line,
        )
        if m is None:
            raise ValueError(f'Fail to parse ps output line: "{line}"')
        pid, spid, _, _, _ = m.groups()  # -> pid, spid, tty, time, cmd
        tids.append(int(spid))

    return tids
