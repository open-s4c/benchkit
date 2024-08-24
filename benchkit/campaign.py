# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to manage campaigns. Campaigns are the main unit of execution of benchmarks.
A campaign is roughly 1 benchmark + N variables. A campaign also defines how the benchkit iterates
over the variables.
"""

import datetime
import glob
import multiprocessing
import os
import os.path
import pathlib
import shutil
import sys
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark
from benchkit.lwchart import (
    DataframeProcessor,
    generate_chart_from_multiple_csvs,
    generate_chart_from_single_csv,
    identical_dataframe,
    generate_global_csv_file,
)
from benchkit.platforms import Platform, get_current_platform
from benchkit.utils.dir import parentdir
from benchkit.utils.misc import seconds2pretty
from benchkit.utils.types import Constants, PathType, Pretty
from benchkit.utils.variables import cartesian_product


_BENCHKIT_CAMPAIGN_CMD_FILE = "/tmp/benchkit-campaign.sh"


class Campaign:
    """
    Simple representation of a campaign of experiments.
    It is the parent of all possible benchkit campaigns.
    """

    parameters = {}

    def __init__(
        self,
        debug: bool,
        gdb: bool,
        enable_data_dir: bool,
        continuing: bool,
    ):
        self._check_parameters_integrity()

        self._enable_data_dir = enable_data_dir
        self._continuing = continuing

        params: Dict[str, Any] = self.parameters

        bds = None
        if "benchmark_duration_seconds" in params:
            bds = params.get("benchmark_duration_seconds")

        for param_key in ["benchmark", "experiment_name", "benchmark_name", "nb_runs"]:
            if param_key not in params:
                raise ValueError(f'Ill formed self.parameters: missing "{param_key}" key.')

        self._benchmark = params.get("benchmark")
        self._benchmark.configure_variables(
            experiment_name=params.get("experiment_name"),
            benchmark_name=params.get("benchmark_name"),
            csv_output_path=self.csv_output_abs_path(),
            base_data_dir=self.base_data_dir(),
            benchmark_duration_seconds=bds,
            nb_runs=params.get("nb_runs"),
            constants=params.get("constants"),
            variables=params.get("variables"),
            pretty_variables=params.get("pretty"),
            debug=debug,
            gdb=gdb,
        )


    def csv_file(
        self,
        campaign_name: str,
        suffix: str = "",
        benchmark_platform: Platform | None = None,
    ) -> str:
        """
        Return the CSV filename corresponding to this campaign run.

        Args:
            campaign_name (str):
                name of the campaign.
            suffix (str, optional):
                suffix of the campaign.
                Defaults to "".
            benchmark_platform (Platform, optional):
                platform where the benchmark is running.
                If None, take the platform associated with the benchmark of the campaign.
                Defaults to None.

        Returns:
            str: the CSV filename corresponding to this campaign run.
        """
        local_platform_name = get_current_platform().hostname
        # hack that only works when there is a single benchmark with a single platform:
        remote_platform_name = (
            benchmark_platform.hostname
            if benchmark_platform is not None
            else self._benchmark.platform.hostname
        )
        platform_names = (
            local_platform_name
            if local_platform_name == remote_platform_name
            else f"{local_platform_name}_{remote_platform_name}"
        )

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        now_str = now.strftime("%Y%m%d_%H%M%S_%f")

        name_no_ext = f"{campaign_name}_{platform_names}{suffix}_{now_str}"
        name_ext = f"{name_no_ext}.csv"

        return name_ext

    def csv_output_abs_path(self) -> pathlib.Path:
        """
        Return the path to the CSV output results of this campaign.

        Returns:
            pathlib.Path: the path to the CSV output results of this campaign.
        """
        csv_output_file = pathlib.Path(self.parameters.get("result_csv_path"))

        if self._continuing:
            # Remove date from csv_output_file and search if any file already exists
            csv_output_file_no_date = "_".join(str(csv_output_file).split("_")[:-2])
            csv_output_cur_files = glob.glob(f"{csv_output_file_no_date}*.csv")

            if csv_output_cur_files:
                # Note: Sort of output files is likely unnecessary
                csv_output_cur_files.sort()

                # Pick last file in list in order to obtain the most recent
                # csv file
                csv_output_file = pathlib.Path(csv_output_cur_files[-1])
                self.parameters["result_csv_path"] = csv_output_file

        csv_output_path = csv_output_file.resolve()
        return csv_output_path

    def base_data_dir(self) -> Optional[PathType]:
        """
        Return the path of the base data directory where the data associated to each run of this
        campaign is stored.

        Returns:
            Optional[PathType]:
                the path of the base data directory where the data associated to each run of this
                campaign is stored.
        """
        if not self._enable_data_dir:
            return None

        result_csv_path = self.parameters.get("result_csv_path")
        data_dir = pathlib.Path(os.path.splitext(result_csv_path)[0])

        abs_data_dir = data_dir.resolve()
        if not abs_data_dir.is_dir():
            os.makedirs(abs_data_dir)

        return abs_data_dir

    def campaign_run(
        self,
        other_campaigns_seconds: int,
        barrier: Optional[multiprocessing.Barrier],
    ) -> None:
        """
        Run a single campaign among other campaigns in a suite.

        Args:
            other_campaigns_seconds (int):
                time remaining to execute other campaigns in the suite.
            barrier (Optional[multiprocessing.Barrier]):
                if needed, the barrier used to synchronize different benchmarks.
        """
        # Workaround to trunc this global file, before logging refactoring TODO
        self._init_cmd_file()

        csv_output_dir = os.path.dirname(self.csv_output_abs_path())
        os.makedirs(csv_output_dir, exist_ok=True)

        self._benchmark.check_dependencies()
        self._benchmark.run(
            other_campaigns_seconds=other_campaigns_seconds,
            barrier=barrier,
            continuing=self._continuing,
        )
        self._move_cmd_file()

    def run(self):
        """
        Run a single campaign, forwarding the call to `campaign_run`.
        """
        self.campaign_run(other_campaigns_seconds=0, barrier=None)

    def campaign_duration_seconds(self) -> int:
        """
        Return the estimated time to execute the whole campaign of experiments.

        Returns:
            int: the estimated time to execute the whole campaign of experiments.
        """
        return self._benchmark.expected_total_duration_seconds()

    def campaign_nb_runs(self) -> int:
        """
        Return the total number of single experiment runs there is in this campaign.

        Returns:
            int: the total number of single experiment runs there is in this campaign.
        """
        return self._benchmark.total_nb_runs()

    def generate_graph(
        self,
        plot_name: str | List[str],
        prefix: str = "",
        **kwargs,
    ) -> None:
        """
        Generate a Seaborn graph with the results of the current campaign.

        Args:
            plot_name (str | List[str]):
                name of the (seaborn) plot.
            prefix (str, optional):
                prefix for the filename of the chart to generate. Defaults to "".
        """
        base_data_dir = self.base_data_dir()
        if base_data_dir is None:
            print(
                "[WARNING] Attempt to generate graph without data dir enabled. Skipping.",
                file=sys.stderr,
            )
            return

        result_csv_path = os.path.abspath(self.parameters.get("result_csv_path"))

        generate_chart_from_single_csv(
            csv_pathname=result_csv_path,
            output_dir=base_data_dir,
            plot_name=plot_name,
            prefix=prefix,
            **kwargs,
        )

    def _check_parameters_integrity(self) -> None:
        if not hasattr(self, "parameters"):
            raise ValueError('Campaign has no "parameters" attribute.')

        if self.parameters is None:
            raise ValueError('Campaign has no "parameters" attribute.')

        if not self.parameters:
            raise ValueError('Campaign has no "parameters" attribute.')

        if "nb_runs" not in self.parameters:
            raise ValueError('Campaign parameters dict has no "nb_runs" field.')

    def _init_cmd_file(self) -> None:
        with open(_BENCHKIT_CAMPAIGN_CMD_FILE, "w") as f:
            header = ["#!/bin/sh", "set -e", ""]
            f.writelines(f"{line}\n" for line in header)

    def _move_cmd_file(self) -> None:
        bdd = self.base_data_dir()
        if bdd is not None:
            dst_path = pathlib.Path(bdd) / "commands.sh"
            shutil.move(_BENCHKIT_CAMPAIGN_CMD_FILE, dst_path)



class CampaignSuite:
    """
    Represent a sequential suite of campaigns.
    """

    def __init__(
        self,
        campaigns: Iterable[Campaign],
    ):
        self._campaigns = list(campaigns)
        self._durations = None
        self._result_csv_paths = None

    @property
    def result_csv_paths(self):
        if self._result_csv_paths is None:
            self._result_csv_paths = [pathlib.Path(os.path.abspath(c.parameters["result_csv_path"])) for c in self._campaigns]
        return self._result_csv_paths

    def durations(self) -> List[int]:
        """
        Return the durations of every campaign in the suite.

        Returns:
            List[int]: the durations of every campaign in the suite.
        """
        if self._durations is None:
            self._durations = [c.campaign_duration_seconds() for c in self._campaigns]
        return self._durations

    def run_suite(
        self,
        parallel: bool = False,
    ) -> None:
        """
        Run the suite of campaign, running sequentially or in parallel each campaign in the suite.

        Args:
            parallel (bool, optional):
                whether to run campaigns in the suite in parallel. Defaults to False.
        """
        durations = self.durations()

        if None in durations:  # if benchmark_duration_seconds is not used in campaign
            remaining = [0 for _ in durations]
        else:
            remaining = [sum(durations[i + 1 :]) for i in range(len(durations))]

        process_list = []
        barrier = multiprocessing.Barrier(len(self._campaigns))

        if not parallel:
            for campaign, remaining_seconds in zip(self._campaigns, remaining):
                campaign.campaign_run(other_campaigns_seconds=remaining_seconds, barrier=None)
        else:
            for campaign in self._campaigns:
                p = multiprocessing.Process(
                    target=campaign.campaign_run,
                    args=(0, barrier),
                )
                process_list.append(p)
                p.start()

        for p in process_list:
            p.join()

    def print_durations(self) -> None:
        """
        Print beautifully in logging the durations of all the campaigns.
        """
        runs = [c.campaign_nb_runs() for c in self._campaigns]
        durations = self.durations()

        for i, (r, d) in enumerate(zip(runs, durations), start=1):
            duration_suffix = ""
            if d is not None:
                duration_suffix = f" - {d:12} seconds - {seconds2pretty(d)}"
            print(f"Campaign {i:2}: {r:8} runs{duration_suffix}")

        sum_runs = sum(runs)
        sum_duration_suffix = ""
        if None not in durations:
            sum_durations = sum(durations)
            sum_duration_suffix = f" - {sum_durations:12} seconds - {seconds2pretty(sum_durations)}"
        print("-" * 64)
        print(f"Total: {sum_runs:14} runs{sum_duration_suffix}")
        print("-" * 64)

    def generate_graph(
        self,
        plot_name: str | List[str],
        process_dataframe: DataframeProcessor = identical_dataframe,
        **kwargs,
    ) ->  None:
        """Generate a global graph for all the campaigns in the suite.

        Args:
            plot_name (str | List[str]):
                name of the (Seaborn) plot to generate.
            process_dataframe (DataframeProcessor, optional):
                callback function to process the dataframe before it is plotted.
                Defaults to identical_dataframe.
        """
        campaign_paths = [bdd for c in self._campaigns if (bdd := c.base_data_dir()) is not None]
        suite_path_tentative = os.path.commonprefix(campaign_paths)
        if os.path.isdir(suite_path_tentative):
            suite_path = pathlib.Path(suite_path_tentative)
        elif suite_path_tentative:
            suite_path = parentdir(suite_path_tentative)
        else:
            suite_path_tentative = os.path.commonprefix(self.result_csv_paths)
            if os.path.isdir(suite_path_tentative):
                suite_path = pathlib.Path(suite_path_tentative)
            else:
                suite_path = parentdir(suite_path_tentative)

        generate_chart_from_multiple_csvs(
            csv_pathnames=self.result_csv_paths,
            plot_name=plot_name,
            output_dir=suite_path,
            process_dataframe=process_dataframe,
            **kwargs,
        )

    def generate_graphs(
        self,
        **kwargs,
    ) -> None:
        """
        Generate one graph per campaign in the suite.
        The arguments are the same as the `Campaign.generate_graph` function.
        """
        for campaign in self._campaigns:
            campaign.generate_graph(**kwargs)

    def generate_global_csv(
        self,
        process_dataframe: DataframeProcessor = identical_dataframe,
        **kwargs,
    ) -> None:
        output_dir = pathlib.Path(os.path.commonpath(self.result_csv_paths))
        if not output_dir.is_dir():
            output_dir = output_dir.parent
        generate_global_csv_file(
            csv_pathnames=self.result_csv_paths,
            output_dir=output_dir,
        )



class CampaignTemplate(Campaign):
    """
    Template of an actual campaign.
    """

    def __init__(
        self,
        name: str,
        benchmark: Benchmark,
        nb_runs: int,
        variables: Iterable[Dict[str, Any]],
        constants: Constants,
        debug: bool,
        gdb: bool,
        enable_data_dir: bool,
        continuing: bool,
        benchmark_duration_seconds: Optional[int] = None,
        results_dir: Optional[PathType] = None,
        pretty: Pretty | None = None,
    ):
        csv_filename = self.csv_file(
            campaign_name="benchmark",
            suffix=f"_{name}",
            benchmark_platform=benchmark.platform,
        )
        if results_dir is None:
            result_csv_path = f"results/{csv_filename}"
        else:
            result_csv_path = pathlib.Path(results_dir) / csv_filename

        # hack that only works when there is a single benchmark with a single platform:
        platform = benchmark.platform
        all_constants = {
            "hostname": platform.hostname,
            "architecture": platform.architecture,
        }
        if constants is not None:
            all_constants.update(constants)

        list_variables = list(variables)

        variable_names = {key for record in list_variables for key in record}
        constant_names = set(all_constants)
        common_names = constant_names.intersection(variable_names)

        if common_names:
            common_names_str = ", ".join(common_names)
            raise ValueError(
                f"Campaign: duplicate names in both constants and variables: {common_names_str}"
            )

        self.parameters = {
            "experiment_name": name,
            "benchmark_name": type(benchmark).__name__.lower(),
            "result_csv_path": result_csv_path,
            "benchmark": benchmark,
            "nb_runs": nb_runs,
            "constants": all_constants,
            "variables": list_variables,
        }

        if benchmark_duration_seconds is not None:
            self.parameters["benchmark_duration_seconds"] = benchmark_duration_seconds

        if pretty is not None:
            self.parameters["pretty"] = pretty

        super().__init__(
            debug=debug, gdb=gdb, enable_data_dir=enable_data_dir, continuing=continuing
        )


class CampaignIterateVariables(CampaignTemplate):
    """
    Campaign where all the records with their parameters values are provided.
    The benchmark will simply iterate over all the values provided in the `variables` iterator.
    """

    def __init__(
        self,
        name: str,
        benchmark: Benchmark,
        nb_runs: int,
        variables: Iterable[Dict[str, Any]],
        constants: Constants,
        debug: bool,
        gdb: bool,
        enable_data_dir: bool,
        continuing: bool = False,
        benchmark_duration_seconds: Optional[int] = None,
        results_dir: Optional[PathType] = None,
        pretty: Pretty | None = None,
    ):
        super().__init__(
            name=name,
            benchmark=benchmark,
            nb_runs=nb_runs,
            variables=list(variables),
            constants=constants,
            debug=debug,
            gdb=gdb,
            enable_data_dir=enable_data_dir,
            continuing=continuing,
            benchmark_duration_seconds=benchmark_duration_seconds,
            results_dir=results_dir,
            pretty=pretty,
        )


class CampaignCartesianProduct(CampaignTemplate):
    """
    Campaign where all variable values are given independently.
    A cartesian product on all variables is applied, such that all combinations
    are tested.
    """

    def __init__(
        self,
        name: str,
        benchmark: Benchmark,
        nb_runs: int,
        variables: Dict[str, Iterable[Any]],
        constants: Constants,
        debug: bool,
        gdb: bool,
        enable_data_dir: bool,
        continuing: bool = False,
        benchmark_duration_seconds: Optional[int] = None,
        results_dir: Optional[PathType] = None,
        pretty: Pretty | None = None,
    ):
        records_gen = cartesian_product(variables)
        super().__init__(
            name=name,
            benchmark=benchmark,
            nb_runs=nb_runs,
            variables=records_gen,
            constants=constants,
            debug=debug,
            gdb=gdb,
            enable_data_dir=enable_data_dir,
            continuing=continuing,
            benchmark_duration_seconds=benchmark_duration_seconds,
            results_dir=results_dir,
            pretty=pretty,
        )
