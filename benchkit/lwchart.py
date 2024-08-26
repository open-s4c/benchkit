# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
lwchart -- for "light-weight chart".

This module does not make use of the helpers in "charts" directory, as
it is intended to be run alongside a campaign, in a possibly minimal
environment.  Thus, we support dynamically importing the data science
dependencies, only in case they are present in the environment.
The chart can be generated only if those are present.
Otherwise, the generation is skipped (with a warning).
"""

import datetime
import importlib.util
import os
import pathlib
import sys
from typing import List, Protocol

from benchkit.utils.types import PathType

libs = ["pandas", "matplotlib", "seaborn"]
if any(importlib.util.find_spec(lib) is None for lib in libs):
    _LIBRARIES_ENABLED = False
    DataFrame = None  # pylint: disable=invalid-name
else:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns
    from pandas import DataFrame

    _LIBRARIES_ENABLED = True


class DataframeProcessor(Protocol):
    """
    Functions that apply a modification on a dataframe before it is plotted.
    """

    def __call__(
        self,
        dataframe: DataFrame,
    ) -> DataFrame: ...


def identical_dataframe(dataframe: DataFrame) -> DataFrame:
    """
    Dataframe processor that does not do any change to the dataframe.

    Args:
        dataframe (DataFrame): the given dataframe to not touch.

    Returns:
        DataFrame: the given dataframe, untouched.
    """
    return dataframe


def _print_warning() -> None:
    print(
        (
            f"[WARNING] Attempt to generate charts while not all "
            f'libraries are present ({", ".join(libs)}), skipping.'
        ),
        file=sys.stderr,
    )


def _generate_timestamp() -> str:
    result = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    return result


def _generate_chart_from_df(
    df: DataFrame,
    plot_name: str | List[str],
    output_dir: PathType,
    prefix: str = "",
    xlabel: str | None = None,
    ylabel: str | None = None,
    process_dataframe: DataframeProcessor = identical_dataframe,
    **kwargs,
) -> None:
    if not _LIBRARIES_ENABLED:
        _print_warning()
        return

    df = process_dataframe(dataframe=df)
    if not isinstance(df, DataFrame):
        raise ValueError("process_dataframe callback is not returning a pandas DataFrame.")

    # TODO refactor with the other df management routines:
    if "global_count" in df.columns and "duration" in df.columns and "throughput" not in df.columns:
        df["throughput"] = df["global_count"] / df["duration"]

    plot_functions = [plot_name] if isinstance(plot_name, str) else list(plot_name)
    args = dict(kwargs)

    title = "Benchkit results"
    if "title" in args:
        title = args["title"]
        del args["title"]

    if "catplot" != plot_name:
        fig = plt.figure(dpi=150)
        chart = fig.add_subplot()

        for plot_function in plot_functions:
            sns_plot_fun = getattr(sns, plot_function)
            chart = sns_plot_fun(
                data=df,
                ax=chart,
                **args,
            )

        if hasattr(chart, "set_title"):
            chart.set_title(title)

        if xlabel is not None:
            chart.set_xlabel(xlabel)
        if ylabel is not None:
            chart.set_ylabel(ylabel)
        fig.tight_layout()
    else:
        chart = sns.catplot(
            data=df,
            **args,
        )
        chart.fig.suptitle(title)
        chart.fig.subplots_adjust(top=0.9)  # Adjust the layout to make space for the title
        fig = chart.fig

    os.makedirs(output_dir, exist_ok=True)

    fig_id = 1
    timestamp = _generate_timestamp()
    output_path = pathlib.Path(output_dir)
    while (fig_path_png := output_path / f"benchkit-{prefix}{timestamp}-{fig_id:02}.png").exists():
        fig_id += 1
    with open(fig_path_png, 'x'):  # avoid overwriting if the figures aren't created yet (race issue)
        pass

    fig.savefig(f"{fig_path_png}", transparent=False)
    print(f'[INFO] Saving campaign figure in "{fig_path_png}"')

    fig_path = pathlib.Path(fig_path_png.with_name(fig_path_png.stem))
    fig.savefig(f"{fig_path}.pdf", transparent=False)
    print(f'[INFO] Saving campaign figure in "{fig_path}.pdf"')

    plt.show()
    plt.close()


def _read_csv(
    csv_pathname: PathType,
    nan_replace: bool,
):
    result = pd.read_csv(
        csv_pathname,
        sep=";",
        comment="#",
        engine="python",
        keep_default_na=nan_replace,  # when True, input values "None" are interpreted as "NaN"
    )
    return result


def generate_chart_from_single_csv(
    csv_pathname: PathType,
    plot_name: str | List[str],
    output_dir: PathType = "/tmp/figs",
    nan_replace: bool = True,
    process_dataframe: DataframeProcessor = identical_dataframe,
    **kwargs,
) -> None:
    """
    Generate a chart from a single CSV file.

    Args:
        csv_pathname (PathType):
            path to the CSV file.
        plot_name (str | List[str]):
            name of the (Seaborn) plot to generate.
        output_dir (PathType, optional):
            directory where to create the file of the chart.
            Defaults to "/tmp/figs".
        nan_replace (bool, optional):
            whether to fill NaN values to replace None, empty strings, etc.
            when parsing the dataset.
        process_dataframe (DataframeProcessor, optional):
            function to process the dataframe to apply a transformation before plotting.
            Defaults to identical_dataframe.
    """
    if not _LIBRARIES_ENABLED:
        _print_warning()
        return

    df = None
    try:
        df = _read_csv(csv_pathname=csv_pathname, nan_replace=nan_replace)
    except pd.errors.EmptyDataError:
        pass

    if df is None:
        return  # empty dataframe, no chart to generate

    _generate_chart_from_df(
        df=df,
        process_dataframe=process_dataframe,
        plot_name=plot_name,
        output_dir=output_dir,
        **kwargs,
    )


def generate_chart_from_multiple_csvs(
    csv_pathnames: List[PathType],
    plot_name: str | List[str],
    output_dir: PathType = "/tmp/figs",
    xlabel: str | None = None,
    ylabel: str | None = None,
    nan_replace: bool = True,
    process_dataframe: DataframeProcessor = identical_dataframe,
    **kwargs,
) -> None:
    """
    Generate a chart from data contained in multiple CSV files.

    Args:
        csv_pathnames (List[PathType]):
            list of paths to the CSV files.
        plot_name (str | List[str]):
            name of the (Seaborn) plot to generate.
        output_dir (PathType, optional):
            path to the directory where to output the chart.
            Defaults to "/tmp/figs".
        xlabel (str | None, optional):
            label of the x-axis.
            Defaults to None.
        ylabel (str | None, optional):
            label of the y-axis. Defaults to None.
        nan_replace (bool, optional):
            whether to fill NaN values to replace None, empty strings, etc.
            when parsing the dataset.
        process_dataframe (DataframeProcessor, optional):
            function to process the dataframe to apply a transformation before plotting.
            Defaults to identical_dataframe.
    """
    if not _LIBRARIES_ENABLED:
        _print_warning()
        return

    global_dataframe = get_global_dataframe(csv_pathnames=csv_pathnames, nan_replace=nan_replace)

    _generate_chart_from_df(
        df=global_dataframe,
        process_dataframe=process_dataframe,
        plot_name=plot_name,
        output_dir=output_dir,
        xlabel=xlabel,
        ylabel=ylabel,
        **kwargs,
    )


def get_global_dataframe(
    csv_pathnames: List[PathType],
    nan_replace: bool = True,
) -> DataFrame:
    if not _LIBRARIES_ENABLED:
        _print_warning()
        return

    dataframes = [
        df
        for p in csv_pathnames
        if (df := _read_csv(csv_pathname=p, nan_replace=nan_replace)) is not None
    ]
    result = pd.concat(dataframes)
    return result


def generate_global_csv_file(
    csv_pathnames: List[PathType],
    output_dir: PathType = "/tmp/figs",
    nan_replace: bool = True,
) -> None:
    if not _LIBRARIES_ENABLED:
        _print_warning()
        return

    ts = _generate_timestamp().replace("-", "_")
    output_file = pathlib.Path(output_dir) / f"benchmark_{ts}.csv"
    global_dataframe = get_global_dataframe(csv_pathnames=csv_pathnames, nan_replace=nan_replace)
    global_dataframe.to_csv(path_or_buf=output_file, sep=";", index=False)
    print(f'[INFO] Saving campaigns common CSV file in "{output_file}"')
