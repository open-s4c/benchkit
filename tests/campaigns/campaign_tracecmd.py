#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchmarks.cprogram import CProgramBench

from benchkit.campaign import CampaignIterateVariables
from benchkit.commandattachments.tracecmd import TraceCmd
from benchkit.platforms import get_current_platform
import os
from benchkit.charts.gant import parse_file, plot_and_save_graph


def find_and_plot_graph_out(
    start_dir: str,
    first_pid: int,
) -> None:
    """
    Recursively searches for all occurrences of 'generate-graph.out' in the directory tree
    starting from 'start_dir' and runs the graph parsing and plotting function for each found file.

    Args:
    - start_dir (str): The directory to start the search from.
    """
    for root, dirs, files in os.walk(start_dir):
        if "generate-graph.out" in files:
            graph_out_path = os.path.join(root, "generate-graph.out")
            print(f"Found: {graph_out_path}")

            try:
                # Call the function to parse and process the file
                threads, last_timestamp, nb_of_cpus = parse_file(graph_out_path, first_pid)

                print(threads)

                # Construct the output filename in the same directory as the .out file
                output_filename = os.path.join(root, "graph.html")

                # Plot and save the graph in the same directory
                plot_and_save_graph(threads, last_timestamp, output_filename, nb_of_cpus)
                print(
                    (
                        f'Processed, plotted data from file "{graph_out_path}",'
                        f'saved as "{output_filename}".'
                    )
                )
            except Exception as e:
                print(f"Error occurred while processing {graph_out_path}: {e}")

def main() -> None:
    platform = get_current_platform()

    traceCmd = TraceCmd(["sched"], platform)
    campaign = CampaignIterateVariables(
        name="attach",
        benchmark=CProgramBench(
            command_attachments=[traceCmd.attachment],
            post_run_hooks=[traceCmd.post_run_hook],
        ),
        nb_runs=1,
        variables=[{}],
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
    )

    campaign.run()
    find_and_plot_graph_out(
        start_dir=campaign.base_data_dir(),
        first_pid=traceCmd.pid,
    )


if __name__ == "__main__":
    main()
