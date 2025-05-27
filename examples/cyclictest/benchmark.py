# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import collections
import matplotlib.pyplot as plt
import numpy

from benchkit.benchmark import WriteRecordFileFunction
from benchkit.campaign import Benchmark
from benchkit.dependencies.packages import PackageDependency
from benchkit.lwchart import _generate_chart_from_df, generate_chart_from_single_csv
from benchkit.shell.shell import shell_out
from benchkit.utils.dir import get_curdir
from benchkit.shell.shellasync import AsyncProcess
from benchkit.campaign import CampaignCartesianProduct
from benchkit.utils.types import PathType
from benchkit.hooks.stressNg import StressNgPreHook, StressNgPostHook

import json
import math
import re
import pathlib
from typing import Any, Dict, List, Optional
import seaborn
import pandas

_bench_src_path = get_curdir(__file__)


class CyclictestBenchhmark(Benchmark):
    def __init__(
        self,
        duration,
        buckets=42,
        percentile=0.95,
    ) -> None:
        """
        Creates a benchmark to measure the latency using `cyclictest` when running `stress-ng` as a stressor.

        Args:
            duration (number):
                How long the benchmark should run.
                The actual experiment will take longer, since `stress-ng` runs for the given duration, but takes a while afterwards to tear down everything.
            buckets (int):
                The amount of buckets that should be displayed on the graph.
                Default is `42`.
            percentile (float):
                Which percentile to show in the second graph.
                This graph is created because sometimes there are some large outliers.
                Default is `0.95`
        """
        stressNgPreHook = StressNgPreHook(duration)
        stressNgPostHook = StressNgPostHook(stressNgPreHook)
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=[
                self.acquire_sudo_pre_run_hook,
                stressNgPreHook,
            ],
            post_run_hooks=[stressNgPostHook],
        )
        self._stress_ng_process = None
        self._counter = []
        self._buckets = buckets
        self._maxLatencyPercentile = 0
        self._maxLatency = 0
        self._percentile = percentile

    @property
    def bench_src_path(self) -> pathlib.Path:
        return _bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return ["interval"]

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [PackageDependency("stress-ng")]

    def build_bench(self, **_kwargs) -> None:
        pass

    def single_run(
        self,
        benchmark_duration_seconds,
        interval,
        **kwargs,
    ) -> str | AsyncProcess:
        run_command = [
            "sudo",
            "cyclictest",
            "--verbose",
            "--mlockall",
            "--interval=" + str(interval),
            "--priority=99",
            "--threads",
            f"--duration={benchmark_duration_seconds}s",
        ]

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=run_command,
            current_dir=pathlib.Path("."),
            environment=None,
            wrapped_environment=None,
            print_output=False,
        )
        return output

    def parse_output_to_results(
        self,
        command_output: str,
        record_data_dir: PathType,
        **kwargs,
    ) -> Dict[str, Any]:
        res = dict()
        results = re.split("\n|:", command_output)
        res["max_CPUs"] = int(results.pop(0).split("=")[1].strip())
        res["online_CPUs"] = int(results.pop(0).split("=")[1].strip())
        res["latency"] = results.pop(0).split(" ")[4]
        i = 0
        while results[0] == f"Thread {i} Interval":
            results.pop(0)
            res[f"thread{i}_interval"] = int(results.pop(0).strip())
            i += 1
        res["threads"] = i
        key_seq_values = [int(s.strip(), 10) for s in results if s]
        df = pandas.DataFrame(
            {
                "thread": key_seq_values[::3],
                "interval": key_seq_values[1::3],
                "latency": key_seq_values[2::3],
            }
        )
        # Get the min, max and mean latencies for each thread to be returned as the final result.
        # All the values are stored separately in a JSON file to keep the CSV file readable, and because you cannot know beforehand how high the latencies will go,
        # meaning that the CSV headers can't be decided beforehand, and would have to differ between runs.
        complete_output = res.copy()
        for thread, row in df.groupby("thread").mean().iterrows():
            res[f"thread{thread}_mean"] = row["latency"]
        for thread, row in df.groupby("thread").max().iterrows():
            res[f"thread{thread}_max"] = int(row["latency"])
        for thread, row in df.groupby("thread").min().iterrows():
            res[f"thread{thread}_min"] = int(row["latency"])
        for _, row in df.iterrows():
            inner = complete_output.get(f"thread{row['thread']}", [])
            inner.append(int(row["latency"]))
            complete_output[f"thread{row['thread']}"] = inner
        with open(pathlib.Path(record_data_dir) / "cyclictest_result.json", "w") as fp:
            json.dump(complete_output, fp)

        df = pandas.DataFrame(
            numpy.array(list(collections.Counter(df["latency"]).items())),
            columns=["latency", "amount"],
        )
        maxLatency = df["latency"].max(numeric_only=True, skipna=True, axis=None)
        self._maxLatency = max(maxLatency, self._maxLatency)
        self._maxLatencyPercentile = round(
            max(df["latency"].quantile(self._percentile), self._maxLatencyPercentile)
        )

        self._counter.append(df)
        bins = min(maxLatency, self._buckets)
        binWidth = math.ceil(maxLatency / bins)
        df["bin"] = pandas.cut(df["latency"], bins=range(0, maxLatency + binWidth, binWidth))
        df["avgAmount"] = df.groupby("bin", observed=False)["amount"].transform(
            lambda df: df.sum() / 10
        )
        avgDf = df.groupby("bin", observed=False)["avgAmount"].mean().reset_index()
        avgDf = avgDf.fillna(0, axis=1)

        # Plot the latencies for this run
        plt.figure()
        plt.xticks(rotation=90)
        ax = seaborn.barplot(
            data=avgDf,
            x="bin",
            y="avgAmount",
            fill=True,
        )
        ax.set_xlabel("Latency")
        ax.set_ylabel("Occurences")
        ax.set_title("Cyclictest latency, Run: " + str(self._nb_runs_done))
        ax.set_yscale("log")
        fig = ax.get_figure()
        fig.savefig(pathlib.Path(record_data_dir) / "cyclictest.png")
        fig.savefig(pathlib.Path(record_data_dir) / "cyclictest.pdf")
        return res

    def acquire_sudo_pre_run_hook(self, **_kwargs):
        # Used to acquire super user privileges before starting the benchmark
        # This is necessary because the `cyclictest`, which is used inside of the `single_run` function, requires `sudo`,
        # but `stress_ng`, which is run before `cyclictest` in a hook, does not.
        # To ensure that you have root priviliges before starting `stress_ng`, `sudo` is ran first, before `stress_ng`.
        shell_out(["sudo", "true"])

    def finalResults(self) -> pandas.DataFrame:
        """
        Get the final panda dataframes, which combines all of the results.

        Returns:
            (DataFrame, DataFrame): A dataframe detailing, for each run, how many times a latency in a given bin occured, and a dataframe detailing the same,
                but only including the data for the percentile provided in the init function.
        """
        res = None
        resPercentile = None
        for df in self._counter:
            bins = min(self._maxLatency, self._buckets)
            binsPercentile = min(self._maxLatencyPercentile, self._buckets)
            binWidth = math.ceil(self._maxLatency / bins)
            binWidthPercentile = math.ceil(self._maxLatencyPercentile / binsPercentile)
            dfPercentile = df.copy()
            df["bin"] = pandas.cut(
                df["latency"], bins=range(0, self._maxLatency + binWidth, binWidth)
            )
            dfPercentile["bin"] = pandas.cut(
                dfPercentile["latency"],
                bins=range(0, self._maxLatencyPercentile + binWidthPercentile, binWidthPercentile),
            )
            df = (
                df.groupby("bin", observed=False)["avgAmount"]
                .mean()
                .reset_index()
                .fillna(0, axis=1)
            )
            dfPercentile = (
                dfPercentile.groupby("bin", observed=False)["avgAmount"]
                .mean()
                .reset_index()
                .fillna(0, axis=1)
            )
            if res is None:
                res = df
                resPercentile = dfPercentile
            else:
                res = pandas.concat([res, df])
                resPercentile = pandas.concat([resPercentile, dfPercentile])
        return (res, resPercentile)


def main() -> None:
    duration = 1
    campaign = CampaignCartesianProduct(
        name="benchmark_name",
        benchmark=CyclictestBenchhmark(duration),
        nb_runs=3,
        variables={"interval": [100]},
        constants={"duration": duration},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        pretty={},
        # This is given to `stress-ng` using the `--timeout` flag, it is not guaranteed that the
        # benchmark will only run for the given amount of seconds, but it is guaranteed that the
        # benchmark will run for at least the given amount of seconds.
        benchmark_duration_seconds=duration,
    )

    campaign.run()
    data_dir = campaign.base_data_dir()
    (res, resPercentile) = campaign._benchmark.finalResults()

    def process(chart):
        chart.set_yscale("log")
        chart.tick_params(axis="x", rotation=90)

    _generate_chart_from_df(
        res,
        title="Cyclictest latency",
        plot_name="barplot",
        xlabel="latency",
        x="bin",
        ylabel="Occurrences",
        y="avgAmount",
        output_dir=data_dir,
        process_chart=process,
        errorbar="ci",
    )
    _generate_chart_from_df(
        resPercentile,
        title="Cyclictest latency, " + str(campaign._benchmark._percentile * 100) + " percentile",
        plot_name="barplot",
        xlabel="latency",
        x="bin",
        ylabel="Occurrences",
        y="avgAmount",
        output_dir=data_dir,
        process_chart=process,
        errorbar="ci",
    )


if __name__ == "__main__":
    main()
