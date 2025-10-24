#!/usr/bin/env python3
# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from heater_parallel import HeaterParBench

from benchkit.benchmark import CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.lwchart import get_global_dataframe
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.dir import get_curdir
from benchkit.utils.misc import hostname
from benchkit.utils.types import PathType


def heater_par_campaign(
    name: str = "parallel_heater_campaign",
    benchmark: Optional[HeaterParBench] = None,
    src_dir: Optional[PathType] = None,
    build_dir: Optional[str] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    benchmark_duration_seconds: float = 0.05,
    nb_runs: int = 10,
    core1: Iterable[int] = (0),
    core2: Iterable[int] = (0),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the Parallel Heater benchmark."""
    variables = {
        "core1": core1,
        "core2": core2,
    }

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = HeaterParBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
            build_dir=build_dir,
        )

    return CampaignCartesianProduct(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        constants=constants,
        debug=debug,
        gdb=gdb,
        enable_data_dir=enable_data_dir,
        continuing=continuing,
        benchmark_duration_seconds=benchmark_duration_seconds,
        results_dir=results_dir,
        pretty=pretty,
    )


def main() -> None:
    """Main function of the campaign script."""

    # Where is the benchmark code located
    src_dir = (get_curdir(__file__) / "").resolve()

    # Define the campaign
    campaign = heater_par_campaign(
        src_dir=src_dir,
        nb_runs=3,
        core1=range(0, os.cpu_count()),
        core2=range(0, os.cpu_count()),
    )

    campaign.run()

    df = get_global_dataframe([campaign.csv_output_abs_path()])

    def df_to_heatmap_matrix(
        df: pd.DataFrame,
        i_col: str = "core1",
        j_col: str = "core2",
        value_col: str = "ops",
        agg: Union[str, Callable] = "median",
        cores: Optional[int] = None,
        drop_outliers: bool = False,
        outlier_threshold: int = 10,
        fill_value: float = np.nan,
    ) -> np.ndarray:
        """
        Build a square (N x N) matrix M where M[i, j] is the aggregated value
        for the (core1=i, core2=j) pair.
        """
        x = df.copy()

        if drop_outliers:
            x = x[x[value_col] > outlier_threshold]

        if cores is None:
            n = int(max(x[i_col].max(), x[j_col].max())) + 1
        else:
            n = int(cores)

        # aggregate
        grouped = x.groupby([i_col, j_col])[value_col]
        if isinstance(agg, str):
            agg_series = getattr(grouped, agg)()
        else:
            agg_series = grouped.aggregate(agg)

        # pivot to full square matrix
        mat = agg_series.unstack(fill_value=np.nan)
        mat = mat.reindex(index=range(n), columns=range(n))
        mat = mat.fillna(fill_value).to_numpy()

        return mat

    def plot_core_heatmap(
        matrix: np.ndarray,
        title: str = "Heatmap of Core Combinations",
        annotate: bool = False,
        fmt: str = ".0f",
        invert_y: bool = True,
        output_image_path: str | None = None,
    ):
        """
        Plot a heatmap from a 2D numpy array.
        """
        plt.figure(figsize=(9, 7))
        ax = sns.heatmap(matrix, annot=annotate, fmt=fmt, cbar=True, linewidths=0)
        if invert_y:
            ax.invert_yaxis()
        ax.set_xlabel("core2")
        ax.set_ylabel("core1")
        ax.set_title(title)
        if output_image_path:
            plt.savefig(output_image_path, bbox_inches="tight", dpi=200)
        plt.show()

    # Build matrix with median ops per (core1, core2)
    M = df_to_heatmap_matrix(df, value_col="ops", agg="median", drop_outliers=False)
    out = out = Path.cwd() / f"heatmap_{hostname()}.pdf"

    plot_core_heatmap(
        M, title=f"Heatmap of core combinations on {hostname()}", output_image_path=out
    )


if __name__ == "__main__":
    main()
