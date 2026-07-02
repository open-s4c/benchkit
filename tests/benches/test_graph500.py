#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Campaign script for Graph500 benchmark with perf analysis.

Demonstrates:
- Running Graph500 with different scales and versions
- Using perf command wrapper for performance counters
"""

from pathlib import Path

from benchkit.benches.graph500 import Graph500Bench
from benchkit import CampaignCartesianProduct
from benchkit.campaign import CampaignSuite
from benchkit.commandwrappers.perf import PerfStatWrap
from benchkit.utils.dir import get_curdir


def graph500_campaign(
    name: str = "graph500_campaign",
    src_dir: Path | None = None,
    results_dir: Path | None = None,
    nb_runs: int = 5,
    use_perf: bool = True,
) -> CampaignCartesianProduct:
    """
    Create a Graph500 campaign with multiple configurations.

    Args:
        name: Campaign name.
        src_dir: Source directory.
        results_dir: Output directory for results.
        nb_runs: Number of runs per configuration.
        use_perf: Enable perf stat wrapper for hardware counters.

    Returns:
        Configured campaign ready to run.
    """
    bench = Graph500Bench()

    command_wrappers = []
    if use_perf:
        perf_wrap = PerfStatWrap(
            events=[
                "cycles",
                "instructions",
                "L1-dcache-loads",
                "L1-dcache-load-misses",
                "L1-dcache-stores",
                "L1-dcache-store-misses",
                "l2d_cache_rd",
                "l2d_cache_refill",
                "cache-references",
                "cache-misses",
                "dTLB-load-misses",
                "branch-misses",
                "mem_access_rd",
                "mem_access_wr",
            ]
        )
        command_wrappers.append(perf_wrap)

    campaign = CampaignCartesianProduct(
        name=name,
        benchmark=bench,
        nb_runs=nb_runs,
        variables={
            "version": [
                "bfs",
                "bfs_sssp",
            ],  # bfs_sssp runs bfs_sssp binary but skips bfs kernel to only run sssp
            "scale": [1, 5, 10, 14, 18, 22],
            "skip_validation": [True],
            "edge_factor": [4, 8, 16],
        },
        command_wrappers=command_wrappers,
        results_dir=results_dir,
    )

    return campaign


def main() -> None:
    """
    Run Graph500 campaign and generate plots.
    """
    results_dir = (get_curdir(__file__) / "results").resolve()  # for easy access to the results

    use_perf = True
    campaign_basic = graph500_campaign(
        name="graph500",
        results_dir=results_dir,
        nb_runs=2,
        use_perf=use_perf,
    )

    campaigns = [campaign_basic]
    suite = CampaignSuite(campaigns=campaigns)

    suite.print_durations()
    suite.run_suite()

    edge_palette = {
        4: "#90e0ef",
        8: "#00b4d8",
        16: "#0077b6",
        32: "#03045e",
    }

    suite.generate_graph(
        plot_name="lineplot",
        x="scale",
        y="harmonic_mean_TEPS",
        hue="edge_factor",
        style="algorithm",
        palette=edge_palette,
        ylabel="Harmonic Mean TEPS",
        xlabel="Scale Factor (2^scale vertices)",
        title="Graph500 BFS vs SSSP Performance",
    )

    suite.generate_graph(
        plot_name="lineplot",
        x="scale",
        y="median_TEPS",
        hue="edge_factor",
        style="algorithm",
        palette=edge_palette,
        ylabel="Median TEPS",
        xlabel="Scale Factor (2^scale vertices)",
        title="Graph500 BFS vs SSSP Median TEPS",
    )

    suite.generate_graph(
        plot_name="lineplot",
        x="scale",
        y="harmonic_stddev_TEPS",
        hue="edge_factor",
        style="algorithm",
        palette=edge_palette,
        ylabel="Harmonic TEPS Stddev",
        xlabel="Scale Factor (2^scale vertices)",
        title="Graph500 BFS vs SSSP TEPS Variability",
    )

    suite.generate_graph(
        plot_name="lineplot",
        x="scale",
        y="mean_time",
        hue="edge_factor",
        style="algorithm",
        palette=edge_palette,
        ylabel="Mean Time (s)",
        xlabel="Scale Factor (2^scale vertices)",
        title="Graph500 BFS vs SSSP Mean Time",
    )

    suite.generate_graph(
        plot_name="lineplot",
        x="scale",
        y="stddev_time",
        hue="edge_factor",
        style="algorithm",
        palette=edge_palette,
        ylabel="Time Stddev (s)",
        xlabel="Scale Factor (2^scale vertices)",
        title="Graph500 BFS vs SSSP Time Variability",
    )

    suite.generate_graph(
        plot_name="lineplot",
        x="scale",
        y="median_time",
        hue="edge_factor",
        style="algorithm",
        palette=edge_palette,
        ylabel="Median Time (s)",
        xlabel="Scale Factor (2^scale vertices)",
        title="Graph500 BFS vs SSSP Median Time",
    )

    suite.generate_graph(
        plot_name="lineplot",
        x="scale",
        y="graph_generation",
        hue="edge_factor",
        style="algorithm",
        palette=edge_palette,
        ylabel="Graph Generation Time (s)",
        xlabel="Scale Factor (2^scale vertices)",
        title="Graph500 Graph Generation Time by Scale",
    )

    suite.generate_graph(
        plot_name="lineplot",
        x="scale",
        y="construction_time",
        hue="edge_factor",
        style="algorithm",
        palette=edge_palette,
        ylabel="Construction Time (s)",
        xlabel="Scale Factor (2^scale vertices)",
        title="Graph500 Graph Construction Time by Scale",
    )

    if use_perf:
        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_IPC",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="Instructions Per Cycle (IPC)",
            xlabel="Scale Factor",
            title="Graph500 Efficiency (IPC): BFS vs SSSP",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_L1_miss_rate",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="L1 D-Cache Miss Rate (%)",
            xlabel="Scale Factor",
            title="Graph500 L1 Cache Efficiency: BFS vs SSSP",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_cache_miss_rate",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="LLC Miss Rate (%)",
            xlabel="Scale Factor",
            title="Graph500 LLC Efficiency: BFS vs SSSP",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_L1-dcache-load-misses",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="L1 Load Misses (Count)",
            xlabel="Scale Factor",
            title="Graph500 L1 Cache Load Misses",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_L1-dcache-stores",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="L1 Stores (Count)",
            xlabel="Scale Factor",
            title="Graph500 L1 Cache Write Traffic",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_cache-misses",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="LLC Misses (Count)",
            xlabel="Scale Factor",
            title="Graph500 LLC Misses",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_l2d_cache_refill",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="L2 D-Cache Refills (Count)",
            xlabel="Scale Factor",
            title="Graph500 L2 Cache Refills",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_dTLB-load-misses",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="dTLB Load Misses (Count)",
            xlabel="Scale Factor",
            title="Graph500 Data TLB Misses",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_branch-misses",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="Branch Prediction Misses",
            xlabel="Scale Factor",
            title="Graph500 Branch Predictor Performance",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_mem_access_rd",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="Memory Read Accesses",
            xlabel="Scale Factor",
            title="Graph500 Memory Read Intensity",
        )

        suite.generate_graph(
            plot_name="lineplot",
            x="scale",
            y="perf_mem_access_wr",
            hue="edge_factor",
            style="algorithm",
            palette=edge_palette,
            ylabel="Memory Write Accesses",
            xlabel="Scale Factor",
            title="Graph500 Memory Write Intensity",
        )


if __name__ == "__main__":
    main()
