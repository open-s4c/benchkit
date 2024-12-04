#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

"""
Benchkit support for Volano
"""

import os
import subprocess
import time
from benchkit.commandattachments.tcpdump import TcpDump
from volano import volano_campaign


def main():
    # Define the command to be executed
    command = "./startup.sh server loop openjdk"

    # Define the directory where the command should be executed
    working_directory = os.path.join(os.getcwd(), "deps")

    # Ensure the directory exists
    if not os.path.isdir(working_directory):
        raise FileNotFoundError(f"The directory {working_directory} does not exist")

    process = subprocess.Popen(
        command,
        shell=True,
        cwd=working_directory,
    )

    tcpdump = TcpDump()

    print(f"Started volano server process with PID: {process.pid}")

    # Example: Wait for 10 seconds before terminating the process
    time.sleep(5)
    print("start bench")
    campaign = volano_campaign(
        post_run_hooks=[tcpdump.post_run_hook],
        command_attachments=[tcpdump.attachment],
    )
    campaign.run()

    process.terminate()

    campaign.generate_graph(
        plot_name="barplot",
        x="rooms",
        y="average_throughput",
    )


if __name__ == "__main__":
    main()
