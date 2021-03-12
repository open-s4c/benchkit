# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Management of dataframes that will be plotted using plotbench.
"""

import os
import pathlib
from typing import Dict, Optional

import pandas as pd

from benchkit.charts.analyses import cross_sect
from benchkit.charts.dataframes import get_comments_parameters, get_dataframe
from benchkit.utils.types import PathType

# TODO COPIED FROM CNA REPL

DEFAULT_MEASURED_KEY = "throughput"
DEFAULT_ESTIMATOR = "mean"


def get_dataset(results_path: PathType) -> pd.DataFrame:
    """
    Return dataset parsed from the given CSV file holding results.

    Args:
        results_path (PathType): path to the CSV file holding results.

    Returns:
        pd.DataFrame: the parsed dataframe.
    """
    csv_paths = [
        pathlib.Path(results_path) / pathlib.Path(f)
        for f in os.listdir(results_path)
        if f.endswith(".csv")
    ]
    dataframes = []

    for csv_path in csv_paths:
        csv_filename = os.path.basename(csv_path)

        comments_params = get_comments_parameters(csv_path)

        df = get_dataframe(csv_path)
        if "bench_name" not in df.columns:
            df.insert(
                0,
                "bench_name",
                df["test_name"] if "test_name" in df.columns else df["experiment_name"],
            )
        if "lock_pretty" in df.columns:
            df["lock"] = df["lock_pretty"]

        if "lock" in df.columns:
            # TODO hacky, replace by better handling like in praconc repo
            if df["lock"].isnull().values.all():
                lock_abbrev = csv_filename.split("_")[1]
                lock = f"kernel:{lock_abbrev}"
                df["lock"] = lock

        if "kernel" in comments_params:
            df["kernel_id"] = comments_params["kernel"].split()[2]

        dataframes.append(df)

    dataset = pd.concat(dataframes)

    def get_benchmark_name(row):
        if "benchmark_name" in row:
            return row["benchmark_name"]

        experiment_name = row["experiment_name"] if "experiment_name" in row else ""
        bench_name = row["bench_name"]
        if experiment_name == bench_name or not experiment_name:
            return bench_name
        return f"{experiment_name}/{bench_name}"

    dataset.insert(
        0,
        "benchmark",
        dataset.apply(get_benchmark_name, axis=1),
    )

    return dataset


def get_aggregates(
    dataset: pd.DataFrame,
    cross_section_dict: Dict[str, str],
    color_axis: str,
    x_axis: str,
    y_axis: str,
    column_axis: Optional[str],
    put_ideal_linear: bool,
) -> pd.DataFrame:
    """
    Get aggregates from current dataset according to cross section.

    Args:
        dataset (pd.DataFrame): dataframe to aggregate.
        cross_section_dict (Dict[str, str]): specification of the cross section.
        color_axis (str): name of the dimension for the color on the chart.
        x_axis (str): name of the dimension for the x-axis.
        y_axis (str): name of the dimension for the y-axis.
        column_axis (Optional[str]): name of the dimension for the column axis.
        put_ideal_linear (bool): whether to add an ideal linear scale.

    Returns:
        pd.DataFrame: the aggregated dataset.S
    """

    xdf = cross_sect(
        df=dataset,
        cross_section_dict=cross_section_dict,
        drop_level=True,
    )

    groupby_keys = [
        c
        for c in dict.fromkeys([column_axis, color_axis, x_axis])  # avoid duplicates
        if c is not None
    ]
    gdf = xdf.groupby(groupby_keys)
    tdf = gdf[y_axis]

    aggregates = pd.DataFrame()

    count_key = "count"
    mean_key = f"{y_axis} mean"
    median_key = f"{y_axis} median"
    std_key = f"{y_axis} std"

    aggregates[count_key] = tdf.count()
    aggregates[mean_key] = tdf.mean()
    aggregates[median_key] = tdf.median()
    aggregates[std_key] = tdf.std()

    metrics = [count_key, mean_key, median_key, std_key]
    base_metric = mean_key

    if put_ideal_linear:
        column_values = sorted(xdf[column_axis].unique())
        # an ideal line has to be plotted on each column of the chart
        for column_value in column_values:
            ani = aggregates.xs(column_value, drop_level=False).reset_index()
            x0 = ani[x_axis][0]
            x1 = ani[x_axis][1]
            # baseline is argmax mean for x1 (based on base_metric):
            baseline = ani.iloc[ani[ani[x_axis] == x1][base_metric].idxmax()][color_axis]
            idf = pd.DataFrame(ani[ani[color_axis] == baseline]).reset_index(drop=True)
            idf[color_axis] = "ideal linear"
            for key in metrics:
                y0 = idf[key][0]
                y1 = idf[key][1]
                slope = (y0 - y1) / (x0 - x1)

                for i in range(2, idf.shape[0]):
                    x_i = idf[x_axis][i]
                    y_i = y0 + (slope * (x_i - x0))
                    idf.loc[i, key] = y_i
            idf.set_index(groupby_keys, inplace=True)
            aggregates = pd.concat([aggregates, idf], axis=0)

    return aggregates
