# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.quick import quick_cmd_campaign

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
    campaign = quick_cmd_campaign(
        name="dd_disk_io",
        option_space=optspace,
        make_benchmark=dd_cmdl_exp,
    )
    campaign.run()
