# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Functions to get dataframe from CSV file and compute useful values (like the fairness factor).
"""

from typing import Any, Dict

import pandas as pd

from benchkit.utils.types import PathType


def fairness_factor(row: Dict[str, Any]) -> float:
    """Computes fairness as in the CNA paper.
    The value is in [0.5, 1.0], the lower the fairer is the record.

    Args:
        row (Dict[str, Any]): a single row of the given dataset.

    Returns:
        float: the value of the fairness factor.
    """
    nb_threads = row["nb_threads"]
    thread_array = sorted([row[f"thread_{i}"] for i in range(nb_threads)], reverse=True)
    half_thread_array = thread_array[: len(thread_array) // 2]

    result = sum(half_thread_array) / sum(thread_array)
    return result


def get_dataframe(csv_path: PathType) -> pd.DataFrame:
    """Get dataframe from CSV file, filtering the comment and assuming the "comma" is a ";".

    Args:
        csv_path (PathType): path to the CSV file containing the results.

    Returns:
        pd.DataFrame: dataframe holding the results.
    """
    df = pd.read_csv(
        f"{csv_path}",
        sep=";",
        comment="#",
        engine="python",
    )
    if "global_count" in df.columns and "duration" in df.columns:
        df["throughput"] = df["global_count"] / df["duration"]

    if "thread_0" in df.columns:
        df["fairness"] = df.apply(fairness_factor, axis=1)

    return df


def get_comments_parameters(csv_path):
    """
    returns dictionary with the values present in the comments of the CSV file.
    """
    with open(csv_path, "r") as csv_file:
        comments = [line for line in csv_file if line.strip().startswith("#")]

    tuples = [
        tuple(c.replace("#", "").strip().split(": "))
        for c in comments
        if ": " in c and not c.startswith("##")
    ]

    benchmark_comments_parameters = dict(tuples)

    variables_str = "".join((c[2:] for c in comments if c.startswith("##")))

    benchmark_comments_parameters["variables"] = {}
    if variables_str:
        benchmark_comments_parameters["variables"] = eval(variables_str)

    return benchmark_comments_parameters
