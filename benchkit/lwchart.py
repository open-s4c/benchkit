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
import json
import numpy as np
from typing import Any, Dict, List, Protocol

from numpy import floating, mean

from benchkit.utils.misc import get_benchkit_temp_folder_str
from benchkit.utils.types import PathType

libs = ["pandas", "matplotlib", "seaborn"]
if any(importlib.util.find_spec(lib) is None for lib in libs):
    _LIBRARIES_ENABLED = False
    DataFrame = Any
    Axes = Any
    FacetGrid = Any
else:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns
    from matplotlib.axes import Axes
    from pandas import DataFrame
    from seaborn.axisgrid import FacetGrid

    _LIBRARIES_ENABLED = True


class DataframeProcessor(Protocol):
    """
    Functions that apply a modification on a dataframe before it is plotted.
    """

    def __call__(
        self,
        dataframe: DataFrame,
    ) -> DataFrame: ...


class ChartProcessor(Protocol):
    """
    Functions that apply a modification on a chart before it is plotted.
    """

    def __call__(
        self,
        chart: Axes | FacetGrid,
    ) -> Axes | FacetGrid: ...


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
    process_chart: ChartProcessor | None = None,
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

    if "catplot" == plot_name: 
        chart = sns.catplot(
            data=df,
            **args,
        )
        chart.fig.suptitle(title)

        if process_chart is not None:
            process_chart(chart=chart)

        chart.fig.subplots_adjust(top=0.9)  # Adjust the layout to make space for the title
        fig = chart.fig
    elif "speedup-stack" == plot_name:
        bench_names = df['bench_name'].unique()
        n_benches = len(bench_names)

        sns.set_theme()
        fig, axes = plt.subplots(
                nrows=1,
                ncols=n_benches,
                figsize=(5 * n_benches, 8),
                sharey=True
                )

        fig.suptitle(title + ": " + ", ".join(bench_names), fontsize=18, y=0.98)

        if n_benches == 1:
            axes = [axes]

        colors = sns.color_palette("pastel")

        factors = ['measured', 'gc', 'sync', 'lock', 'other']
        labels = ['Measured', 'Garbage Collection', 'Synchronization Activities',
                'Lock Contention', 'Other Overheads']

        for ax, bench in zip(axes, bench_names):
            bench_df = df[df['bench_name'] == bench]
            speedup_data = _get_speedup_data(bench_df)

            ind = np.arange(len(speedup_data))
            bottom = np.zeros(len(speedup_data))

            for factor, label, color in zip(factors, labels, colors):
                vals = [d[factor] for d in speedup_data.values()]
                ax.bar(ind, vals, bottom=bottom, label=label, color=color)
                bottom += vals

            ax.set_title(bench)
            ax.set_xlabel('Number of Threads')
            ax.set_xticks(ind)
            ax.set_xticklabels([str(k) for k in speedup_data.keys()])
            if ax is axes[0]:
                ax.set_ylabel('Speedup')
            ax.legend(loc='upper left')

        # plt.title(title + ": " + ", ".join(bench_names))
        plt.tight_layout()
        plt.show()
    else:
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

        if process_chart is not None:
            process_chart(chart=chart)

        fig.tight_layout()

    os.makedirs(output_dir, exist_ok=True)

    fig_id = 1
    timestamp = _generate_timestamp()
    output_path = pathlib.Path(output_dir)
    while (fig_path_png := output_path / f"benchkit-{prefix}{timestamp}-{fig_id:02}.png").exists():
        fig_id += 1
    # avoid overwriting if the figures aren't created yet (race issue):
    with open(fig_path_png, "x"):
        pass

    fig.savefig(f"{fig_path_png}", transparent=False)
    print(f'[INFO] Saving campaign figure in "{fig_path_png}"')

    fig_path = pathlib.Path(fig_path_png.with_name(fig_path_png.stem))
    fig.savefig(f"{fig_path}.pdf", transparent=False)
    print(f'[INFO] Saving campaign figure in "{fig_path}.pdf"')

    plt.show()
    plt.close()

def _get_speedup_data(
        df: DataFrame,
        ) -> Dict[str, float]:
    single_threaded_duration = df[df["nb_threads"] == 1]["duration"].values[0]
    single_threaded_gc = df[df["nb_threads"] == 1]["gc"].values[0]
    multithreaded_df = df[df["nb_threads"] != 1]
    data = {}

    for _, row in multithreaded_df.iterrows():
        perfect_speedup_duration = single_threaded_duration / row["nb_threads"]

        measured_component = perfect_speedup_duration / row["duration"]
        gc_component = (row["gc"] - single_threaded_gc) / row["duration"]
        sync_component = (row["context-switches"] / 1000) / row["duration"] 
        lock_component = row["lock"] / row["duration"] 

        other_component = 1 - measured_component - gc_component - sync_component - lock_component
        # print(measured_component + gc_component + sync_component + lock_component)
        # print("other: " + str(other_component))
        
        data[row["nb_threads"]] = {
                'measured' : measured_component * row["nb_threads"],
                'gc' : gc_component * row["nb_threads"],
                'sync' : sync_component * row["nb_threads"],
                'lock' : lock_component * row["nb_threads"],
                'other' : other_component * row["nb_threads"]}
    return data

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
    output_dir: PathType = f"{get_benchkit_temp_folder_str()}/figs",
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
            Defaults to "/tmp/benchkit-[USERNAME]/figs".
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
    output_dir: PathType = f"{get_benchkit_temp_folder_str()}/figs",
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
            Defaults to "/tmp/benchkit-[USERNAME]/figs".
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

def generate_chart_from_multiple_csvs_and_jsons(
    csv_pathnames: List[PathType],
    json_pathnames: List[List[PathType]],
    plot_name: str | List[str],
    output_dir: PathType = "/tmp/figs",
    xlabel: str | None = None,
    ylabel: str | None = None,
    nan_replace: bool = True,
    process_dataframe: DataframeProcessor = identical_dataframe,
    **kwargs,
) -> None:
    """
    Generate a chart from data contained in multiple CSV files and JSON files.

    Args:
        csv_pathnames (List[PathType]):
            list of paths to the CSV files.
        json_pathnames (List[List[PathType]]):
            list of list of paths to the JSON files.
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

    csv_dataframe = get_global_dataframe(csv_pathnames=csv_pathnames, nan_replace=nan_replace)

    csv_useful_columns = ["gc", "duration", "lock"] 
    csv_non_useful_columns = ["rep"]

    csv_grouping_columns = [col for col in csv_dataframe.columns if col not in csv_useful_columns + csv_non_useful_columns]
    csv_dataframe = csv_dataframe.groupby(
            csv_grouping_columns,
            as_index=False
            )[csv_useful_columns].mean()

    json_dataframe = get_global_dataframe_from_jsons(json_pathnames=json_pathnames)
    json_dataframe = json_dataframe.drop(csv_useful_columns + csv_non_useful_columns, axis=1)

    global_dataframe = pd.merge(csv_dataframe, json_dataframe, on=csv_grouping_columns, how="outer")

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

def _process_json(
        json_path: PathType,
        ) -> Dict[str, int]:
    with open(json_path, 'r') as f:
        data = json.load(f)
    
        output = {}
        total_context_switches = 0
        
        for entry in data:
            for k, v in entry.items():
                # Count context-switch events
                if k.endswith("/context-switches"):
                    total_context_switches += int(v)
                elif "context-switches" not in k:
                    output[k] = v
                    
        output["context-switches"] = total_context_switches            
        return output

def _process_jsons(
        json_paths: List[PathType],
        ) -> Dict[str, floating[Any]]:
     data = [_process_json(p) for p  in json_paths]

     data_without_context_switches = {k: v for k, v in data[0].items() if k != "context-switches"}
     context_switches = [d["context-switches"] for d in data]
     data_without_context_switches["context-switches"] = mean(context_switches)
     return data_without_context_switches

def get_global_dataframe_from_jsons(
    json_pathnames: List[List[PathType]],
) -> DataFrame:
    if not _LIBRARIES_ENABLED:
        _print_warning()
        return

    dataframes = [
            _process_jsons(ps)
            for ps in json_pathnames
    ]
    result = pd.DataFrame(dataframes)
    return result

def generate_global_csv_file(
    csv_pathnames: List[PathType],
    output_dir: PathType = f"{get_benchkit_temp_folder_str()}/figs",
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
