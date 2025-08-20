# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `perf` Linux utility which allows to capture performance monitoring values
when executing the wrapped command. Wrappers can execute "perf record" and "perf stat".

This wrapper is used when using perf on the JVM
"""

import pathlib
import re
import sys
import time
from typing import Any, Dict, List, Optional

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandwrappers.perf import PerfReportWrap, PerfStatWrap
from benchkit.helpers.linux import ps, sysctl
from benchkit.platforms import Platform
from benchkit.shell.shell import shell_interactive, shell_out
from benchkit.shell.shellasync import AsyncProcess, SplitCommand
from benchkit.utils.types import PathType


def _perf_command_prefix(
    perf_bin: PathType,
    platform: Platform,
) -> SplitCommand:
    kernel_perf_event_paranoid = sysctl.get_kernel_perf_event_paranoid(comm_layer=platform.comm)
    if -1 == kernel_perf_event_paranoid:
        return [perf_bin]

    print(
        (
            '[WARNING] perf tool will be run using "sudo". '
            "To avoid this, enable perf in userspace with the following command:\n"
            "  sudo sysctl -w kernel.perf_event_paranoid=-1  # transient\n"
            '  echo "kernel.perf_event_paranoid=-1" | sudo tee -a /etc/sysctl.conf  '
            "# permanent across reboots"
        ),
        file=sys.stderr,
    )
    return ["sudo", perf_bin]


def _is_jvm_thread(thread_name: str) -> bool:
    name = thread_name.strip()
    jvm_names = [
        "GC",
        "G1",
        "VM",
        "Reference Handl",
        "Finalizer",
        "Signal Dispatch",
        "Service Thread",
        "C2",
        "C1",
        "Sweeper thread",
        "VM Periodic Tas",
        "Common-Cleaner",
    ]
    for jvm_name in jvm_names:
        if name.startswith(jvm_name):
            return True

    return False


class JavaPerfStatWrap(PerfStatWrap):
    """Command wrapper for the `perf stat` utility."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def attach_every_thread(
        self,
        process: AsyncProcess,
        platform: Platform,
        record_data_dir: pathlib.Path,
        poll_ms: int = 10,
    ):
        """Command attachment that will attach to every thread of the wrapped process.

        Args:
            process (AsyncProcess): the process to attach perf-stat to.
            platform (Platform): the platform where the process is running.
            record_data_dir (pathlib.Path): the path to the record data directory of the benchmark.
            poll_ms (int, optional): the period at which to poll the process to detect newly created
                                     threads. Defaults to 10.
        """
        perf_prefix = _perf_command_prefix(perf_bin=self._perf_bin, platform=platform)
        prefix = perf_prefix + ["stat"] + self.perf_stat_options + ["--per-thread", "-t"]

        tids2perf_cmd = {}

        while not process.is_finished():
            current_tids = ps.get_threads_of_process_with_names(pid=process.pid)
            for name, tid in current_tids:
                if not _is_jvm_thread(name):
                    if tid not in tids2perf_cmd:
                        value_pathname = record_data_dir / f"perf-stat-val-tid{tid}.txt"
                        cmd = prefix + [f"{tid}", "--output", f"{value_pathname}"]
                        tids2perf_cmd[tid] = AsyncProcess(
                            platform=platform,
                            arguments=cmd,
                            stdout_path=record_data_dir / f"perf-stat-out-tid{tid}.txt",
                            stderr_path=record_data_dir / f"perf-stat-err-tid{tid}.txt",
                        )

            time.sleep(poll_ms / 1000)

        for current_process in tids2perf_cmd.values():
            try:
                current_process.wait()
            except AsyncProcess.AsyncProcessError:
                pass
        self._every_thread_cleanup(record_data_dir=record_data_dir)

    # TODO: Look into different version of perf. This might not be needed.
    # Remove this fix when #231 is merged.
    def _get_perf_field(self, perf_counter_row: dict, field: str, perf_version: str):
        if perf_version == "6.8.12" or perf_version == "6.17.rc2.gb19a97d57c15":
            match field:
                case "event_name":
                    return perf_counter_row["event"]
                case "counter_value":
                    return perf_counter_row["counter-value"]
                case "counter_unit":
                    return perf_counter_row["unit"]
                case "run_time":
                    return perf_counter_row["event-runtime"]
                case "percentage_counter_cover":
                    return perf_counter_row["pcnt-running"]
                case _:
                    raise ValueError(f"No field named {field} known for this version of perf")
        else:
            return perf_counter_row[field]

    def _results_per_thread(
        self,
        perf_stat_pathname: PathType,
    ) -> RecordResult:
        perf_version_output = shell_out(
            "perf --version", print_output=False
        )  # TODO: Cache this result
        perf_version = perf_version_output.split(" ")[2].strip()

        counter_rows = self._parse_csv(  # TODO adapt for json
            perf_stat_pathname=perf_stat_pathname,
            field_names=["taskname-pid"] + self._perf_stat_csv_field_names,
        )

        m = re.match(pattern=r"^.*-val-tid(\d+).txt$", string=perf_stat_pathname)
        if m is None:
            raise ValueError(f"No tid in filename: {perf_stat_pathname}")
        filename_tid = int(m.groups()[0])

        output_dict = {}
        for counter_row in counter_rows:
            taskname_pid = counter_row["taskname-pid"]
            _, pid = taskname_pid.rsplit("-", maxsplit=1)
            assert filename_tid == int(pid)

            # event_name = counter_row["event_name"]
            event_name = self._get_perf_field(counter_row, "event_name", perf_version)
            if event_name.endswith("/"):
                event_name = event_name[:-1]
            # counter_value = counter_row["counter_value"]
            counter_value = self._get_perf_field(counter_row, "counter_value", perf_version)
            # unit = counter_row["counter_unit"]
            unit = self._get_perf_field(counter_row, "counter_unit", perf_version)
            # run_time = counter_row["run_time"]
            run_time = self._get_perf_field(counter_row, "run_time", perf_version)
            # coverage = counter_row["percentage_counter_cover"]
            coverage = self._get_perf_field(counter_row, "percentage_counter_cover", perf_version)

            output_dict[f"perf-stat/pid{pid}/{event_name}"] = counter_value
            output_dict[f"perf-stat/pid{pid}/{event_name}.unit"] = unit
            output_dict[f"perf-stat/pid{pid}/{event_name}.rt"] = run_time
            output_dict[f"perf-stat/pid{pid}/{event_name}.cov"] = coverage

        return output_dict

    def _results_global(
        self,
        perf_stat_pathname: PathType,
    ) -> RecordResult:
        counter_rows = self._parse(
            perf_stat_pathname=perf_stat_pathname,
            field_names=self._perf_stat_csv_field_names,
        )

        output_dict = {}
        for counter_row in counter_rows:
            event_name = counter_row["event"]
            if event_name is None:
                continue
            if event_name.endswith("/"):
                event_name = event_name[:-1]
            counter_value = counter_row["counter-value"]
            unit = counter_row["unit"]
            run_time = counter_row["event-runtime"]
            coverage = counter_row["pcnt-running"]  # percentage_counter_cover

            output_dict[f"perf-stat/{event_name}"] = counter_value
            output_dict[f"perf-stat/{event_name}.unit"] = unit
            output_dict[f"perf-stat/{event_name}.rt"] = run_time
            output_dict[f"perf-stat/{event_name}.cov"] = str(coverage)

        return output_dict


class JavaPerfReportWrap(PerfReportWrap):
    """Command wrapper for the `perf record`/`perf report` utility."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def attach_every_thread(
        self,
        process: AsyncProcess,
        platform: Platform,
        record_data_dir: pathlib.Path,
    ):
        """Command attachment that will attach to every thread of the wrapped process.

        Args:
            process (AsyncProcess): the process to attach perf-stat to.
            platform (Platform): the platform where the process is running.
            record_data_dir (pathlib.Path): the path to the record data directory of the benchmark.
            poll_ms (int, optional): the period at which to poll the process to detect newly created
                                     threads. Defaults to 10.
        """
        perf_prefix = _perf_command_prefix(perf_bin=self._perf_bin, platform=platform)
        prefix = (
            ["sudo"] + perf_prefix + ["record"] + self.perf_record_options + ["--inherit", "-p"]
        )

        perf_data_pathname = record_data_dir / f"perf-record-val-pid{process.pid}.data"
        self.latest_perf_path = perf_data_pathname

        cmd = prefix + [f"{process.pid}", "--output", f"{perf_data_pathname}"]
        self.platform.comm.shell(command=cmd)

    def post_run_hook_report(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> Optional[Dict[str, Any]]:
        """Post run hook to generate extension of result dict holding the results of perf report.

        Args:
            experiment_results_lines (List[RecordResult]): the record results.
            record_data_dir (PathType): path to the record data directory.
            write_record_file_fun (WriteRecordFileFunction): callback to record a file into data
                                                             directory.
        """
        assert experiment_results_lines and record_data_dir

        perf_data_pathname = self.latest_perf_path
        self._chown(pathname=perf_data_pathname)

        command = self._perf_script_command(perf_data_pathname=perf_data_pathname)

        # retrieve output into file first for posterity
        if self._report_file:
            file_command = command
            output = shell_out(file_command, print_output=False)

            write_record_file_fun(file_content=output.strip(), filename="perf.report")

            processed_script_data = self._process_perf_script_report(output)
            return {"lock": processed_script_data}

        if self._report_interactive:
            shell_interactive(command=command, ignore_ret_codes=(-13,))  # ignore broken pipe error

    def _process_perf_script_report(
        self,
        output: str,
    ) -> float:

        allowed_threads = re.compile(r"^(?:java|pool-\d+-thread-\d+)$", re.IGNORECASE)

        wait_start = {}
        total_wait_time = 0.0
        total_wait_time_per_thread = {}

        for line in output.splitlines():
            splits = line.split()
            if not allowed_threads.match(splits[0]):
                continue

            if len(splits) == 17 or len(splits) == 8:
                timestamp = float(splits[3][:-1])
                thread_id = int(splits[1])
                wait_start[thread_id] = timestamp

            elif len(splits) == 6:
                timestamp = float(splits[3][:-1])
                thread_id = int(splits[1])
                key_to_remove = None

                # Find the corresponding futex enter event for this thread
                for key in wait_start.keys():
                    if key == thread_id:  # Match on thread ID
                        start_time = wait_start[key]
                        wait_time = (timestamp - start_time) * 1000
                        total_wait_time += wait_time
                        key_to_remove = key  # Mark key for deletion

                        if thread_id in total_wait_time_per_thread:
                            total_wait_time_per_thread[thread_id] += wait_time
                        else:
                            total_wait_time_per_thread[thread_id] = wait_time
                        break

                # Remove the matched key
                if key_to_remove:
                    del wait_start[key_to_remove]

        mean = sum(total_wait_time_per_thread.values()) / len(total_wait_time_per_thread)
        return mean

    def _perf_script_command(self, perf_data_pathname: PathType) -> SplitCommand:
        command = [
            self._perf_bin,
            "script",
            "--input",
            f"{perf_data_pathname}",
        ] + self.perf_report_options

        return command
