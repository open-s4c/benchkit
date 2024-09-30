#!/usr/bin/env python3
import os
import subprocess
from benchmarks.cprogram import CProgramBench
from benchkit.campaign import CampaignIterateVariables
from benchkit.platforms import get_current_platform
from benchkit.commandattachments.tracecmd import TraceCmd
import sys
import multiprocessing
from benchkit.charts.gant import parse_file, plot_and_save_graph

class MyCampaign:
    
    def __init__(self) -> None:
        self.base_data_dir = ""
        self.traceCmd = None
    

def find_and_plot_graph_out(start_dir: str, first_pid: any) -> None:
    """
    Recursively searches for all occurrences of 'generate-graph.out' in the directory tree
    starting from 'start_dir' and runs the graph parsing and plotting function for each found file.

    Args:
    - start_dir (str): The directory to start the search from.
    """
    for root, dirs, files in os.walk(start_dir,):
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
                print(f"Processed and plotted data from {graph_out_path}, saved as {output_filename}")
            except Exception as e:
                print(f"Error occurred while processing {graph_out_path}: {e}")
def run_campaign(camp):
    """
    This function will run the campaign, intended to be run in a subprocess.
    """
    platform = get_current_platform()
    traceCmd = TraceCmd(["sched"], platform)
    
    campaign = CampaignIterateVariables(
        name="attach",
        benchmark=CProgramBench(
            command_attachments=[traceCmd.attachment],
            post_run_hooks=[traceCmd.post_run_hook]
        ),
        nb_runs=1,
        variables=[{}],
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
    )
    
    campaign.run()
    camp.base_data_dir = campaign.base_data_dir()
    camp.traceCmd = traceCmd

def main() -> None:
    myCampaign = MyCampaign()
    # Run the campaign.run() method in a subprocess
    process = multiprocessing.Process(target=run_campaign(myCampaign))
    process.start()  # Start the subprocess
    process.join()   # Wait for the subprocess to finish
    find_and_plot_graph_out(myCampaign.base_data_dir, myCampaign.traceCmd._pid)

if __name__ == "__main__":
    main()