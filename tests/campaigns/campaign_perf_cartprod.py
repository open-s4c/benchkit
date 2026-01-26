#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import numpy as np
import pandas as pd
from pandas import DataFrame

from benchkit import CampaignCartesianProduct
from benchkit.benches.small.sleep import SleepBench
from benchkit.commandwrappers.perf import PerfStatWrap, enable_non_sudo_perf
from benchkit.platforms import get_current_platform


def add_ylog_scale(chart):
    if hasattr(chart, "set_yscale"):
        chart.set_yscale("log")
    else:
        chart.set(yscale="log")
    return chart


def make_perfstat_process_dataframe(events: list[str]):
    """
    Build a simple process_dataframe that reshapes only perf-stat/<event> columns.

    Args:
        events: list like ["cache-misses", "instructions", "cycles"]

    Returns:
        function(DataFrame) -> DataFrame with columns: stat, value (+ id vars)
    """
    cols = [f"perf-stat/{e}" for e in events]

    def process_dataframe(dataframe: DataFrame) -> DataFrame:
        df = dataframe.copy().replace("<not counted>", np.nan)

        # Keep only present columns (robust if some event missing)
        present = [c for c in cols if c in df.columns]
        if not present:
            # Return empty long df with expected columns
            out = df.iloc[0:0].copy()
            out["stat"] = pd.Series(dtype="object")
            out["value"] = pd.Series(dtype="float64")
            return out[["stat", "value"]]

        # Coerce to numeric
        for c in present:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # id vars: everything that is not a perf-stat column
        id_vars = [c for c in df.columns if not c.startswith("perf-stat/")]

        long = df.melt(
            id_vars=id_vars,
            value_vars=present,
            var_name="stat",
            value_name="value",
        )

        # Make the stat labels nicer: "perf-stat/cycles" -> "cycles"
        long["stat"] = long["stat"].str.replace("perf-stat/", "", regex=False)

        # Stable order on x-axis
        long["stat"] = pd.Categorical(long["stat"], categories=events, ordered=True)

        return long

    return process_dataframe


def main() -> None:
    platform = get_current_platform()
    enable_non_sudo_perf(comm_layer=platform.comm)

    events = ["cache-misses", "instructions", "cycles"]
    perfstatwrap = PerfStatWrap(
        events=events,
        use_json=True,
        aggregate_hybrid=True,
        platform=platform,
    )

    campaign = CampaignCartesianProduct(
        name="strace",
        benchmark=SleepBench(),
        parameter_space={"duration_seconds": [3]},
        nb_runs=1,
        command_wrappers=[perfstatwrap],
        post_run_hooks=[perfstatwrap.post_run_hook_update_results],
        platform=platform,
    )

    campaign.run()

    process_perf = make_perfstat_process_dataframe(events=events)

    campaign.generate_graph(
        plot_name="barplot",
        title=f"perf stat on {platform.comm.hostname()}",
        process_dataframe=process_perf,
        process_chart=add_ylog_scale,
        x="stat",
        y="value",
    )


if __name__ == "__main__":
    main()
