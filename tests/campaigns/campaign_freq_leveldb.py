#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import sys
from typing import List

from leveldb import LevelDBBench

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.campaign import CampaignCartesianProduct
from benchkit.helpers.linux.predictable.cpupower import CPUPower
from benchkit.platforms import Platform, get_current_platform
from benchkit.utils.dir import caller_dir, gitmainrootdir
from benchkit.utils.git import clone_repo
from benchkit.utils.types import PathType

xp_nb_threads = [1, 2, 4, 8, 16, 32]
xp_nb_runs = 10
xp_duration = 10

leveldb_tut_dir = gitmainrootdir() / "tutorials/leveldb-bench"
leveldb_src_dir = caller_dir() / "deps/leveldb"


def repo_prep() -> None:
    clone_repo(
        repo_url="https://github.com/google/leveldb.git",
        repo_src_dir=leveldb_src_dir,
        commit="068d5ee1a3ac40dabd00d211d5013af44be55bea",
        modules=True,
        patches=[
            leveldb_tut_dir / "patch.diff",
        ],
    )


class CpuFrequency:
    def __init__(
        self,
        platform: Platform,
    ) -> None:
        self._platform = platform
        self._nb_cpus = self._platform.nb_cpus()
        self._cpu_power = CPUPower(comm_layer=platform.comm)
        self._saved_governors = None
        self._saved_frequencies_mhz = None

    def setup(self) -> None:
        self._saved_governors = [
            self._cpu_power.get_governor(cpu=cpu) for cpu in range(self._nb_cpus)
        ]
        self._saved_frequencies_mhz = [
            self._cpu_power.get_frequency_mhz(cpu=cpu) for cpu in range(self._nb_cpus)
        ]

    def teardown(self) -> None:
        for cpu in range(self._nb_cpus):
            self._cpu_power.set_frequency(
                frequency_mhz=self._saved_frequencies_mhz[cpu],
                cpus=[cpu],
            )
        for cpu in range(self._nb_cpus):
            self._cpu_power.set_governor(governor=self._saved_governors[cpu], cpus=[cpu])

    def get_frequency_values(self) -> List[int]:
        value = 1500 * (10**6)
        try:
            values = self._cpu_power.get_frequency_values()
        except ValueError:
            print(
                f"[WARNING] No frequency value found with cpupower, setting to {value} Hz",
                file=sys.stderr,
            )
            values = [value]
        return values

    def pre_run_hook(
        self,
        build_variables: RecordResult,
        run_variables: RecordResult,
        other_variables: RecordResult,
        record_data_dir: PathType,
    ) -> None:
        assert build_variables or run_variables or record_data_dir

        frequency: int = other_variables["frequency"] if "frequency" in other_variables else 0
        if not frequency:
            print("[WARNING] Not setting frequency in the PreRunHook", file=sys.stderr)
            return

        frequency_mhz = frequency // (10**6)
        self._cpu_power.set_governor()
        self._cpu_power.set_frequency(frequency_mhz=frequency_mhz)

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        assert experiment_results_lines or record_data_dir or write_record_file_fun

        governors = {
            f"freq_gov_cpu{cpu}": self._cpu_power.get_governor(cpu=cpu)
            for cpu in range(0, self._nb_cpus)
        }
        frequencies = {
            f"freq_val_cpu{cpu}": self._cpu_power.get_frequency_mhz(cpu=cpu)
            for cpu in range(0, self._nb_cpus)
        }
        result = governors | frequencies
        return result


def main() -> None:
    platform = get_current_platform()
    cpufreq = CpuFrequency(platform=platform)
    nb_cpus = platform.nb_cpus()
    frequencies = cpufreq.get_frequency_values()

    cpufreq.setup()
    repo_prep()

    campaign = CampaignCartesianProduct(
        name="freq_leveldb",
        benchmark=LevelDBBench(
            src_dir=leveldb_src_dir,
            command_wrappers=[],
            command_attachments=[],
            shared_libs=[],
            pre_run_hooks=[cpufreq.pre_run_hook],
            post_run_hooks=[cpufreq.post_run_hook],
            platform=platform,
        ),
        nb_runs=xp_nb_runs,
        variables={
            "bench_name": ["readrandom"],
            "nb_threads": [t for t in xp_nb_threads if t < nb_cpus],
            "frequency": frequencies,
        },
        constants=None,
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=xp_duration,
        pretty={"frequency": {f: f"{f//(10**6)} MHz" for f in frequencies}},
    )

    campaign.run()

    campaign.generate_graph(
        title="LevelDB: frequency vs parallelism",
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="frequency_pretty",
        style="frequency_pretty",
        marker="o",
        markers=True,
        dashes=False,
    )

    campaign.generate_graph(
        title="LevelDB: parallelism vs frequency",
        plot_name="lineplot",
        x="frequency_pretty",
        y="throughput",
        hue="nb_threads",
        style="nb_threads",
        marker="o",
        markers=True,
        dashes=False,
    )

    cpufreq.teardown()


if __name__ == "__main__":
    main()
