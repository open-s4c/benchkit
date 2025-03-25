# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import sys

from benchkit.quick import parse_cli_optspace, quick_cmd_evaluate

optspace = {
    "bs": ["4K", "16K", "64K"],
    "count": [1000, 5000, 10000],
}


# Command generator: builds a dd command based on options
def dd_cmdl_exp(optpt) -> str:
    bs = optpt["bs"]
    count = optpt["count"]
    cmd = f"dd if=/dev/zero of=/tmp/tempfile bs={bs} count={count} oflag=direct status=none"
    return cmd


# Run the experiment
if __name__ == "__main__":
    optspace, nb_runs = parse_cli_optspace(
        option_space=optspace,
        cli_args=sys.argv[1:],
    )

    quick_cmd_evaluate(
        name="dd_disk_io",
        option_space=optspace,
        make_benchmark=dd_cmdl_exp,
        nb_runs=nb_runs,
    )
