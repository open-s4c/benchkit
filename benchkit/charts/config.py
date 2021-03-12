# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Get dataset configuration from a json file.
"""

import json
import pathlib
import re
from typing import List


def _get_configuration():
    config_filename = pathlib.Path("config.json")
    config = {}

    if config_filename.is_file():
        with open(config_filename) as file:
            config = json.load(file)

    return config


def _results_hierarchy(results_path):
    def gd(pathname: pathlib.Path):
        filename = pathname.name
        m = re.match(
            pattern=(
                r"(?P<bench>.+)_"
                r"(?P<platform>.+)_"
                r"(?P<experiment>([0-9]+-)?.+)_"
                r"(?P<date>[0-9]{8})_(?P<time>[0-9]{6})[.]csv"
            ),
            string=filename,
        )

        if m is None:
            return None

        gdict = m.groupdict()
        gdict["path"] = pathname
        return gdict

    csv_paths = list(pathlib.Path(results_path).glob("*.csv"))
    group_dicts = [gd(p) for p in sorted(csv_paths)]
    group_dicts = [g for g in group_dicts if g is not None]

    platforms = {}
    for gd in group_dicts:
        plat = gd["platform"]
        if plat not in platforms:
            platforms[plat] = {}
        exp = gd["experiment"]
        if exp not in platforms[plat]:
            platforms[plat][exp] = []
        date = gd["date"]
        time = gd["time"]
        platforms[plat][exp].append(
            {
                "bench": gd["bench"],
                "datetime": f"{date}_{time}",
                "path": gd["path"],
            }
        )
    for plat in platforms:
        for exp in platforms[plat]:
            platforms[plat][exp].sort(key=lambda di: di["datetime"])

    return platforms


class CampaignResults:
    """The results of a campaign with the associated paths (CSV files)."""

    def __init__(
        self,
        results_path,
    ):
        self._results_path = results_path
        self._results_hierarchy = _results_hierarchy(self._results_path)
        self._config = _get_configuration()

    def available_platforms(self) -> List[str]:
        """Get the platforms available in the results.

        Returns:
            List[str]: list of the names of the platforms available in the results.
        """
        return sorted(self._results_hierarchy.keys())

    def available_experiments(self, platform: str) -> List[str]:
        """Get the available experiments of the given platform name in the results.

        Args:
            platform (str): platform name for which the experiments are found.

        Returns:
            List[str]: list of experiment names of the given platform in the results.
        """
        return sorted(self._results_hierarchy.get(platform).keys())

    def csv_path(
        self,
        platform: str,
        experiment: str,
    ) -> str:
        """Get the CSV path of the results on the given platform for the given experiment.
        This function only returns one path, the last one executed.

        Args:
            platform (str): name of the platform for which to get the results.
            experiment (str): name of the experiment for which to get the results.

        Returns:
            str: path to CSV file containing the results.
        """

        # pick the last one (regarding datetime)
        return self._results_hierarchy.get(platform).get(experiment)[-1]["path"]

    def csv_paths(
        self,
        platform: str,
        experiment: str,
    ) -> List[str]:
        """Get the CSV path of the results on the given platform for the given experiment.
        This function returns all the paths found.

        Args:
            platform (str): name of the platform for which to get the results.
            experiment (str): name of the experiment for which to get the results.

        Returns:
            List[str]: list of paths to CSV files containing the results.
        """

        # pick all of them
        paths = [p["path"] for p in self._results_hierarchy.get(platform).get(experiment)]
        return paths
