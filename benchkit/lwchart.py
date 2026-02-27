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
import json
import os
import pathlib
import sys
from typing import Any, Callable, Dict, List, Optional, Protocol

import numpy as np
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
        chart.figure.suptitle(title)

        if process_chart is not None:
            process_chart(chart=chart)

        chart.figure.subplots_adjust(top=0.9)  # Adjust the layout to make space for the title
        fig = chart.figure
    elif "speedup-stack" == plot_name:
        bench_names = df["bench_name"].unique()
        n_benches = len(bench_names)

        sns.set_theme()
        fig, axes = plt.subplots(nrows=1, ncols=n_benches, figsize=(5 * n_benches, 8), sharey=True)

        fig.suptitle(title + ": " + ", ".join(bench_names), fontsize=18, y=0.98)

        if n_benches == 1:
            axes = [axes]

        colors = sns.color_palette("pastel")

        factors = ["measured", "gc", "sync", "lock", "other"]
        labels = [
            "Measured",
            "Garbage Collection",
            "Synchronization Activities",
            "Lock Contention",
            "Other Overheads",
        ]

        for ax, bench in zip(axes, bench_names):
            bench_df = df[df["bench_name"] == bench]

            speedup_data = _get_speedup_data(bench_df, **kwargs)
            # speedup_data = dict(sorted(speedup_data.items()))
            __import__("pprint").pprint(speedup_data)

            ind = np.arange(len(speedup_data))
            bottom = np.zeros(len(speedup_data))

            for component_name, color in zip(next(iter(speedup_data.values())).keys(), colors):
                vals = [d[component_name] for d in speedup_data.values()]
                ax.bar(ind, vals, bottom=bottom, label=component_name, color=color)
                bottom += vals

            ax.set_title(bench)
            ax.set_xlabel("Number of Threads")
            ax.set_xticks(ind)
            ax.set_xticklabels([str(k) for k in speedup_data.keys()])
            if ax is axes[0]:
                ax.set_ylabel("Speedup")
            ax.legend(loc="upper left")

        # plt.title(title + ": " + ", ".join(bench_names))
        plt.tight_layout()
        plt.show()
    elif "java-speedup-stack" == plot_name:
        bench_names = df["bench_name"].unique()
        n_benches = len(bench_names)

        sns.set_theme()
        fig, axes = plt.subplots(nrows=1, ncols=n_benches, figsize=(5 * n_benches, 8), sharey=True)

        fig.suptitle(title + ": " + ", ".join(bench_names), fontsize=18, y=0.98)

        if n_benches == 1:
            axes = [axes]

        colors = sns.color_palette("pastel")

        factors = ["measured", "gc", "sync", "lock", "other"]
        labels = [
            "Measured",
            "Garbage Collection",
            "Synchronization Activities",
            "Lock Contention",
            "Other Overheads",
        ]

        for ax, bench in zip(axes, bench_names):
            bench_df = df[df["bench_name"] == bench]
            speedup_data = _get_java_speedup_data(bench_df)
            speedup_data = dict(sorted(speedup_data.items()))

            ind = np.arange(len(speedup_data))
            bottom = np.zeros(len(speedup_data))

            for factor, label, color in zip(factors, labels, colors):
                vals = [d[factor] for d in speedup_data.values()]
                ax.bar(ind, vals, bottom=bottom, label=label, color=color)
                bottom += vals

            ax.set_title(bench)
            ax.set_xlabel("Number of Threads")
            ax.set_xticks(ind)
            ax.set_xticklabels([str(k) for k in speedup_data.keys()])
            if ax is axes[0]:
                ax.set_ylabel("Speedup")
            ax.legend(loc="upper left")

        # plt.title(title + ": " + ", ".join(bench_names))
        plt.tight_layout()
        plt.show()
    elif "thread-profile" == plot_name:

        all_thread_profiles = (
            kwargs["speedupstackwrapper"].get_threadprofiler().get_per_thread_profiles()
        )
        show_run_number = kwargs["show_run_number"]

        thread_profiles = all_thread_profiles[show_run_number]
        # __import__("pprint").pprint(thread_profiles)
        # tid = list(thread_profiles.keys())[1]
        thread_mapping = {v: i + 1 for i, v in enumerate(sorted(list(thread_profiles.keys())))}

        local_df: DataFrame = df

        # print(thread_profile)
        bench_names = local_df["bench_name"].unique() if ("bench_name" in local_df) else []
        # n_benches = len(bench_names)

        sns.set_theme()
        fig, ax = plt.subplots(figsize=(8, 6))
        # fig.suptitle(title + ": " + ", ".join(bench_names), fontsize=18, y=0.98)

        # colors = sns.color_palette("pastel")
        colors = sns.color_palette()

        state_to_color_map = {
            "SCHEDULED_OUT": colors[1],
            "SCHEDULED_IN": colors[0],
            "THREAD_EXIT": colors[3],
            "MUTEX": colors[4],
            "FUTEX": colors[6],
            "DISK_IO": colors[2],
        }

        # plt.rcParams["patch.edgecolor"] = "none"
        # plt.rcParams["patch.linewidth"] = 0.0

        profile_settings = {
            "edgecolor": "none",
            "linewidth": 0,
        }

        for tid, idx in thread_mapping.items():
            thread_profile = thread_profiles[tid]
            # current_left = 0
            # current_state = "SCHEDULED_OUT"

            for profile_block in thread_profile:
                block_index = profile_block["block_index"]
                block_start_time = profile_block["block_start_time_ns"]
                block_end_time = profile_block["block_end_time_ns"]
                block_total_width = block_end_time - block_start_time
                # first_event_time = profile_block["first_event_time_ns"]
                # last_event_time = profile_block["last_event_time_ns"]
                # end_state = profile_block["end_state"]
                offcpu_time = profile_block["offcpu_time_ns"]
                mutex_time = profile_block["mutex_time_ns"]
                futex_time = profile_block["futex_time_ns"]
                disk_io_time = profile_block["disk_io_time_ns"]
                cutoff_time = profile_block["cutoff_time_ns"]
                # ax.barh(idx, block_total_width, left=block_start_time, color=colors[0])

                # TODO: handle cutoff properly
                current_left = block_start_time

                # if cutoff_time:
                #     # This is the last block of this thread
                #     last_block_width = cutoff_time - block_start_time
                #     if last_block_width > 0:
                #         ax.barh(
                #             idx,
                #             last_block_width,
                #             left=current_left,
                #             label=current_state,
                #             color=state_to_color_map[current_state],
                #             **profile_settings,
                #         )
                #     continue

                # Show part before first event (if it exists)
                # before_part_width = first_event_time - block_start_time
                # if before_part_width > 0:
                #     ax.barh(
                #         idx,
                #         before_part_width,
                #         left=current_left,
                #         label=current_state,
                #         color=state_to_color_map[current_state],
                #         **profile_settings,
                #     )
                #     current_left += before_part_width

                # Show all the components of block
                # total_component_width = last_event_time - first_event_time
                scheduled_in_width = (
                    block_total_width - offcpu_time - mutex_time - futex_time - disk_io_time
                )
                if scheduled_in_width > 0:
                    ax.barh(
                        idx,
                        scheduled_in_width,
                        left=current_left,
                        label="SCHEDULED_IN",
                        color=state_to_color_map["SCHEDULED_IN"],
                        **profile_settings,
                    )
                    current_left += scheduled_in_width

                if disk_io_time > 0:
                    ax.barh(
                        idx,
                        disk_io_time,
                        left=current_left,
                        label="DISK_IO",
                        color=state_to_color_map["DISK_IO"],
                        **profile_settings,
                    )
                    current_left += disk_io_time

                if offcpu_time > 0:
                    ax.barh(
                        idx,
                        offcpu_time,
                        left=current_left,
                        label="SCHEDULED_OUT",
                        color=state_to_color_map["SCHEDULED_OUT"],
                        **profile_settings,
                    )
                    current_left += offcpu_time

                if mutex_time > 0:
                    ax.barh(
                        idx,
                        mutex_time,
                        left=current_left,
                        label="MUTEX",
                        color=state_to_color_map["MUTEX"],
                        **profile_settings,
                    )
                    current_left += mutex_time

                if futex_time > 0:
                    ax.barh(
                        idx,
                        futex_time,
                        left=current_left,
                        label="FUTEX",
                        color=state_to_color_map["FUTEX"],
                        **profile_settings,
                    )
                    current_left += futex_time

                # Show part after last event (if it exists)
                # after_part_width = block_end_time - last_event_time
                # if after_part_width > 0:
                #     ax.barh(
                #         idx,
                #         after_part_width,
                #         left=current_left,
                #         label=end_state,
                #         color=state_to_color_map[end_state],
                #         **profile_settings,
                #     )
                #     current_left += after_part_width

                # current_state = end_state

        ax.set_yticks(list(thread_mapping.values()))
        ax.set_yticklabels(list(thread_mapping.keys()))
        # handles, labels = ax.get_legend_handles_labels()
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))  # removes duplicates
        ax.legend(by_label.values(), by_label.keys())
        # ax.legend(loc="upper left")

        plt.xlabel("Time since boot (ns)")
        plt.ylabel("Thread Identifier (TID)")
        plt.title(title + ": " + ", ".join(bench_names))
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


def time_transformation(
    val: float,
    from_unit: str,
    to_unit: str,
) -> float:
    unit_table = {
        "h": 60 * 60,
        "m": 60,
        "s": 1,
        "ms": 1e-3,
        "us": 1e-6,
        "ns": 1e-9,
    }
    return val * (unit_table[from_unit] / unit_table[to_unit])


def _get_speedup_data(
    df: DataFrame,
    duration_transformation: Optional[Callable[[float], float]],
    speedup_stack_components: dict[str, Callable[[float, float], float]],
    constant_duration: bool = False,
    speed_metric: Optional[str] = None,
    **kwargs,
) -> Dict[int, Dict[str, Any]]:
    mean_df = (
        df.groupby("nb_threads")[
            ["duration"]
            + list(speedup_stack_components.keys())
            + ([speed_metric] if constant_duration else [])
        ]
        .mean()
        .reset_index()
    )
    if duration_transformation:
        mean_df["duration"] = mean_df["duration"].apply(duration_transformation)

    single_threaded_duration = mean_df.loc[mean_df["nb_threads"] == 1, "duration"].iloc[0]
    single_threaded_speed_metric = (
        mean_df.loc[mean_df["nb_threads"] == 1, speed_metric].iloc[0] if speed_metric else 0
    )

    multithreaded_df = mean_df[mean_df["nb_threads"] != 1]
    data: dict[int, dict[str, float]] = {}

    for _, row in multithreaded_df.iterrows():
        nb_threads = row["nb_threads"]

        duration = row["duration"]
        if constant_duration:
            # The benchmark has a constant duration, so compute a duration based on speed metric
            duration = duration / (row[speed_metric] / single_threaded_speed_metric)

        perfect_speedup_duration = single_threaded_duration / nb_threads
        measured_component = perfect_speedup_duration / duration

        # for name, func in speedup_stack_components.items():
        #     print(name, row[name], func(row[name]), func(row[name]) / duration)

        slowdown_components = {
            name: (func(row[name], nb_threads) / duration)
            for name, func in speedup_stack_components.items()
        }

        other_component = 1 - measured_component - sum(slowdown_components.values())

        data[nb_threads] = {
            "measured": measured_component * nb_threads,
            "other": other_component * nb_threads,
        } | {
            name: (component_value * nb_threads)
            for name, component_value in slowdown_components.items()
        }
    return data


def _get_java_speedup_data(
    df: DataFrame,
) -> Dict[str, Dict[str, Any]]:
    single_threaded_duration = df[df["nb_threads"] == 1]["duration"].values[0]
    single_threaded_gc = df[df["nb_threads"] == 1]["gc"].values[0]
    multithreaded_df = df[df["nb_threads"] != 1]
    data = {}

    for _, row in multithreaded_df.iterrows():
        perfect_speedup_duration = single_threaded_duration / row["nb_threads"]

        measured_component = perfect_speedup_duration / row["duration"]
        gc_component = ((row["nb_threads"] * row["gc"]) - single_threaded_gc) / row["duration"]
        sync_component = (row["context-switches"] / 1000) / row["duration"]
        lock_component = row["lock"] / row["duration"]

        other_component = 1 - measured_component - gc_component - sync_component - lock_component

        data[row["nb_threads"]] = {
            "measured": measured_component * row["nb_threads"],
            "gc": gc_component * row["nb_threads"],
            "sync": sync_component * row["nb_threads"],
            "lock": lock_component * row["nb_threads"],
            "other": other_component * row["nb_threads"],
        }
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


def generate_chart_from_multiple_jsons(
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
    Generate a chart from data contained in multiple JSON files.

    Args:
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

    json_dataframe = get_global_dataframe_from_jsons(json_pathnames=json_pathnames)

    _generate_chart_from_df(
        df=json_dataframe,
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
    with open(json_path, "r") as f:
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
    data = [_process_json(p) for p in json_paths]

    # TODO: The processing of json's is currently tightly linked with the
    # processing needed for speedup stacks.
    # This will need to be refactored in order to process arbitrary json.
    data_columns = ["duration", "gc", "lock", "context-switches"]
    information_columns = [
        "experiment_name",
        "benchmark_name",
        "hostname",
        "architecture",
        "bench_name",
        "size",
        "nb_threads",
    ]

    information_data = {k: v for k, v in data[0].items() if k in information_columns}

    for key in data_columns:
        information_data[key] = mean([float(d[key]) for d in data])

    return information_data


def get_global_dataframe_from_jsons(
    json_pathnames: List[List[PathType]],
) -> DataFrame:
    if not _LIBRARIES_ENABLED:
        _print_warning()
        return

    dataframes = [_process_jsons(ps) for ps in json_pathnames]
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
