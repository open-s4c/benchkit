# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.utils.types import PathType


class NsysWrap(CommandWrapper):
    """Command wrapper for the `nsys` profiling utility."""

    def __init__(
        self,
        platform: Platform | None = None,
        other_options: List[str] = (),
    ):
        super().__init__()
        self.platform = platform
        self._other_options = [str(o) for o in other_options]
        self._output_dirname = "nsys_reports"
        self._trace_filename = "report.nsys-rep"

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [PackageDependency("nsys")]

    def command_prefix(
        self,
        record_data_dir: Optional[PathType],
        **kwargs,
    ) -> List[str]:
        if record_data_dir is None:
            raise ValueError("Record data directory is required for nsys output.")
        output_dir = self._output_dir(record_data_dir=record_data_dir)
        trace_file = output_dir / self._trace_filename

        cmd_prefix = super().command_prefix(**kwargs)

        options = ["--output", f"{trace_file}"] + self._other_options
        nsys_prefix = ["nsys", "profile"] + options

        return nsys_prefix + cmd_prefix

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        """
        Post-run hook to extract summary stats from `nsys stats`.
        """
        self._run_nsys_stat(record_data_dir=record_data_dir)
        extracted_stats = self._extract_stats(record_data_dir=record_data_dir)
        return extracted_stats

    def _output_dir(
        self,
        record_data_dir: PathType,
    ) -> Path:
        record_data_dir = self.platform.comm.host_to_comm_path(record_data_dir)
        output_dir = record_data_dir / self._output_dirname
        self.platform.comm.makedirs(path=output_dir, exist_ok=True)
        return output_dir

    def _run_nsys_stat(
        self,
        record_data_dir: PathType,
    ) -> None:
        output_dir = self._output_dir(record_data_dir=record_data_dir)
        trace_file = output_dir / self._trace_filename

        command = ["nsys", "stats", "--format", "csv", "--output", ".", f"{trace_file}"]
        self.platform.comm.shell(command=command, output_is_log=True)

    def _extract_stats(
        self,
        record_data_dir: PathType,
    ) -> Dict[str, str]:
        """Example of statistics that can be extracted from the nsys report."""

        mem_size_path = record_data_dir / self._output_dirname / "report_cuda_gpu_mem_size_sum.csv"
        extracted = {}
        with mem_size_path.open(newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                operation = row["Operation"]
                if operation.startswith("["):
                    operation = operation[1:]
                if operation.endswith("]"):
                    operation = operation[:-1]

                extracted[f"nsys/{operation} (MB)"] = row["Total (MB)"]

        return extracted


class NcuWrap(CommandWrapper):
    """Command wrapper for the `ncu` compute profiler utility."""

    def __init__(
        self,
        platform: Platform,
        csv: bool = True,
        other_options: List[str] = (),
    ):
        super().__init__()

        ext = "csv" if csv else "txt"

        self.platform = platform
        self._csv = csv
        self._other_options = [str(o) for o in other_options]
        self._report_filename = f"ncu_general.{ext}"

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [PackageDependency("ncu")]

    def command_prefix(
        self,
        record_data_dir: Optional[PathType],
        **kwargs,
    ) -> List[str]:
        if record_data_dir is None:
            raise ValueError("Record data directory is required for ncu output.")
        record_data_dir = self.platform.comm.host_to_comm_path(record_data_dir)
        report_path = record_data_dir / self._report_filename

        cmd_prefix = super().command_prefix(**kwargs)

        options = ["--csv", "--log-file", f"{report_path}"] + self._other_options
        ncu_prefix = ["ncu"] + options

        return ncu_prefix + cmd_prefix

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        """
        Post-run hook to extract summary stats from `ncu stats`.
        """
        report_path = record_data_dir / self._report_filename
        report_txt = report_path.read_text()
        report_lines = [
            line.strip() for line in report_txt.splitlines() if not line.startswith("==")
        ]

        csv_reader = csv.DictReader(report_lines)
        stats = {}
        only_numbers_commas_dots = re.compile(r"^[\d,.]+$")
        for row in csv_reader:
            keys = ("ID", "Metric Name")
            unit = row["Metric Unit"]
            value = row["Metric Value"]

            unit_value = f" ({unit})" if unit else ""

            if not value:
                continue

            if only_numbers_commas_dots.match(value):
                value = value.replace(",", "").strip()

            key = "ncu/" + "/".join(row[k] for k in keys) + unit_value
            stats[key] = value
            print()

        return stats
