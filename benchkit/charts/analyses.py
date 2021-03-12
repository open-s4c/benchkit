# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Run the analyses to transform data into printable data (aggregation, cross sections, etc.).
"""


from typing import Any, Dict

import pandas as pd


def cross_sect(
    df: pd.DataFrame,
    cross_section_dict: Dict[str, Any],
    drop_level: bool,
) -> pd.DataFrame:
    """Perform a cross section of the given dataframe according to the specification provided in the
    given dict. Cross section means that we filter the dataframe according to several dimensions by
    specifying, for each wanted dimension, a single value.

    Args:
        df (pd.DataFrame): dataframe on which to perform the cross section.
        cross_section_dict (Dict[str, Any]): cross section specification. For each key (dimension
                                             name), it provides a value on which filtering that
                                             dimension.
        drop_level (bool): whether to drop the cross-sected dimensions.

    Returns:
        pd.DataFrame: the dataframe after executing the cross section.
    """
    index_keys = list(cross_section_dict.keys())
    index_values = list(cross_section_dict.values())
    if len(index_keys) == 0:
        return pd.DataFrame(df)
    if len(index_keys) == 1:
        xdf = df.set_index(index_keys[0])
        return xdf.xs(
            key=index_values[0],
            drop_level=drop_level,
        )
    # len(index_keys) > 1:
    xdf = df.set_index(index_keys)
    return xdf.xs(
        key=tuple(index_values),
        level=tuple(index_keys),
        drop_level=drop_level,
    )


def get_aggregates(
    df: pd.DataFrame,
    cross_section_dict: Dict[str, Any],
) -> pd.DataFrame:
    """Get the aggregated dataframe with several aggregators after cross-secting it.

    Args:
        df (pd.DataFrame): dataframe to aggregate.
        cross_section_dict (Dict[str, Any]): specification of the cross sections to execute.

    Returns:
        pd.DataFrame: the aggregated dataframe.
    """
    xdf = cross_sect(
        df=df,
        cross_section_dict=cross_section_dict,
        drop_level=True,
    )

    gdf = xdf.reset_index().groupby(["lock", "nb_threads"], sort=False)
    tdf = gdf["throughput"]
    fdf = gdf["fairness"]
    ddf = gdf["duration"]

    aggregates = pd.DataFrame()
    aggregates["count"] = tdf.count()
    aggregates["throughput min"] = tdf.min()
    aggregates["throughput max"] = tdf.max()
    aggregates["throughput median"] = tdf.median()
    aggregates["throughput mean"] = tdf.mean()
    aggregates["throughput std"] = tdf.std()
    aggregates["fairness mean"] = fdf.mean()
    aggregates["fairness median"] = fdf.median()
    aggregates["fairness std"] = fdf.std()
    aggregates["duration min"] = ddf.min()
    aggregates["duration max"] = ddf.max()
    aggregates["duration median"] = ddf.median()

    aggregates["lock_pretty"] = gdf["lock_pretty"].first()

    return aggregates
