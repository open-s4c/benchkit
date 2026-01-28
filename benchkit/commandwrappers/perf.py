# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Command wrapper for the `perf` Linux utility which allows to capture performance monitoring values
when executing the wrapped command. Wrappers can execute "perf record" and "perf stat".
"""

import csv
import json
import os
import os.path
import pathlib
import re
import subprocess
import sys
import time
from functools import cache
from typing import Any, Callable, Dict, List, Optional, Tuple

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandwrappers import CommandWrapper, PackageDependency
from benchkit.communication import CommunicationLayer
from benchkit.helpers.linux import ps, sysctl
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shell import shell_interactive, shell_out
from benchkit.shell.shellasync import AsyncProcess, SplitCommand
from benchkit.utils.types import Environment, PathType

PerfEvent = str

FILENAME_FLAMEGRAPH = "flamegraph.svg"


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


def _find(find_dir: PathType, include_subdirs: bool):
    for root, dirs, files in os.walk(find_dir):
        for name in files:
            yield os.path.join(root, name)
        if include_subdirs:
            for name in dirs:
                yield os.path.join(root, name)


def _which(executable: str) -> Optional[PathType]:
    result = None

    try:
        result = shell_out(
            command=f"which {executable}", print_input=False, print_output=False
        ).strip()
    except subprocess.CalledProcessError:
        pass

    return result


@cache
def _find_perf_bin(search_path: Optional[PathType]) -> PathType:
    result = None
    kernel = shell_out(
        "uname -r",
        print_input=False,
        print_output=False,
    ).strip()

    if search_path is not None:
        perf_path = os.path.realpath(os.path.join(search_path, "perf"))
        result = shell_out(f"which {perf_path}").strip()

    if result is None:
        result = _which(f"/tools/{kernel}/bin/perf")

    if result is None:
        result = _which("perf")

    if result is None:
        raise ValueError(
            "Impossible to find perf on the platform. Please install and/or specify search_path."
        )

    return result


def _validate_record_data_dir(record_data_dir: PathType) -> None:
    if record_data_dir is None:
        raise ValueError(
            "Record data directory cannot be None, it is required to save the perf data."
        )


@cache
def _get_available_events(
    perf_bin: PathType,
) -> Tuple[List[str], Dict[str, Dict[str, str]]]:

    raw_output = shell_out(
        command=f"{perf_bin} list --no-desc",
        print_input=False,
        print_output=False,
    )

    events: List[str] = []
    events_dict: Dict[str, Dict[str, str]] = {}
    current_group = "no_group"
    events_dict[current_group] = {}

    iterlines = iter(raw_output.splitlines())
    event_id = None

    for line in iterlines:
        sline = line.strip()

        # New group section
        m = re.match(r"^([-_/%:A-Za-z0-9\s]+):$", sline)
        if m:
            (group_name,) = m.groups()
            current_group = group_name
            events_dict[current_group] = {}
            continue

        # event OR alias [description] (all on one line)
        m = re.match(r"([-_/%:.a-zA-Z0-9]+)\s+OR\s+([-_/%:.a-zA-Z0-9]+)\s*\[(.*)\]", sline)
        if m:
            event_left, event_right, event_desc = m.groups()
            events.extend([event_left, event_right])
            events_dict[current_group][event_left] = event_desc
            events_dict[current_group][event_right] = event_desc
            continue

        # event OR alias (description is on next line)
        m = re.match(r"([-_/%:.a-zA-Z0-9]+)\s+OR\s+([-_/%:.a-zA-Z0-9]+)$", sline)
        if m:
            event_left, event_right = m.groups()
            events.extend([event_left, event_right])
            event_id = (event_left, event_right)
            continue

        # event [description] (canonical case)
        m = re.match(r"([-_/%:.a-zA-Z0-9]+)\s+\[(.*)\]", sline)
        if m:
            event_id, event_desc = m.groups()
            events.append(event_id)
            events_dict[current_group][event_id] = event_desc
            continue

        # Single event name only (description may follow)
        m = re.match(r"(^[-_/%:.a-zA-Z0-9]+)$", sline)
        if m:
            (event_id,) = m.groups()
            events.append(event_id)
            continue

        # Description line in brackets (follows previous event_id)
        m = re.match(r"^\[(.*)\]$", sline)
        if m:
            (event_desc,) = m.groups()
            if isinstance(event_id, tuple):
                for eid in event_id:
                    events_dict[current_group][eid] = event_desc
            elif event_id:
                events_dict[current_group][event_id] = event_desc
            continue

        # Opened bracket, starts multi-line desc
        m = re.match(r"^\[(.*)$", sline)
        if m:
            (event_desc,) = m.groups()
            if isinstance(event_id, tuple):
                for eid in event_id:
                    events_dict[current_group][eid] = event_desc
            elif event_id:
                events_dict[current_group][event_id] = event_desc
            continue

        # Continuation of multi-line description (closing)
        m = re.match(r"^\s+(.*)\]$", line)
        if m:
            (event_desc,) = m.groups()
            if isinstance(event_id, tuple):
                for eid in event_id:
                    events_dict[current_group][eid] += " " + event_desc
            elif event_id:
                events_dict[current_group][event_id] += " " + event_desc
            continue

        # Continuation of multi-line description (middle)
        m = re.match(r"^\s+(.*)$", line)
        if m:
            (event_desc,) = m.groups()
            if isinstance(event_id, tuple):
                for eid in event_id:
                    events_dict[current_group][eid] += " " + event_desc
            elif event_id:
                if event_id not in events_dict[current_group]:
                    events_dict[current_group][event_id] = ""
                events_dict[current_group][event_id] += " " + event_desc
            continue

        # Skip known unstructured lines
        if "[Raw hardware event descriptor]" in sline:
            continue
        if "[Hardware breakpoint]" in sline:
            continue
        if sline.startswith("Error:"):
            continue
        if not sline:
            continue

        raise ValueError(f'perf-stat parsing error, unable to match: "{line}"')

    return events, events_dict


def _validate_events(
    perf_bin: PathType,
    events: List[PerfEvent],
    remove_absent_event: bool,
) -> List[PerfEvent]:
    all_available_events, _ = _get_available_events(perf_bin=perf_bin)

    available_events = []
    for event in events:
        processed_event = event
        if processed_event.endswith(":k") or processed_event.endswith(":u"):
            processed_event = processed_event[:-2]
        if processed_event.startswith("r") and processed_event[1:].isnumeric():
            available_events.append(event)
            continue
        if processed_event in all_available_events:
            available_events.append(event)

    if not remove_absent_event:
        not_available_events = [event for event in events if event not in available_events]
        if not_available_events:
            raise ValueError(
                f"The following provided events are not available: {','.join(not_available_events)}"
            )
    return available_events


def enable_non_sudo_perf(comm_layer: CommunicationLayer) -> None:
    """Allows non-root / non-sudoer to run perf.

    Args:
        comm_layer (CommunicationLayer): communication layer where to enable perf for non-root user.
    """
    current_paranoid_value = sysctl.get_kernel_perf_event_paranoid(comm_layer=comm_layer)
    if -1 != current_paranoid_value:
        sysctl.set_kernel_perf_event_paranoid(value=-1, comm_layer=comm_layer)


class PerfWrapError(Exception):
    """Error for any `perf` related wrapper."""


class PerfStatWrap(CommandWrapper):
    """Command wrapper for the `perf stat` utility."""

    _perf_stat_csv_field_names = [
        "counter-value",
        "unit",
        "event",
        "event-runtime",
        "pcnt-running",  # percentage_counter_cover
        "comment1",
        "comment2",
    ]

    def __init__(
        self,
        perf_path: Optional[PathType] = None,
        events: Optional[List[PerfEvent]] = None,
        freq: Optional[int] = None,
        quiet: Optional[bool] = None,
        output_filename: Optional[PathType] = "perf-stat.txt",
        use_json: bool = True,
        separator: Optional[str] = None,
        remove_absent_event: bool = False,
        aggregate_hybrid: bool = False,
        platform: Platform | None = None,
    ):
        if use_json and separator is not None:
            raise ValueError(
                "PerfStatWrap: Cannot use json format and provide a CSV separator at the same time."
            )

        super().__init__()
        self.platform = get_current_platform() if platform is None else platform

        self._perf_bin = _find_perf_bin(search_path=perf_path)

        if events is not None:
            events = _validate_events(
                perf_bin=self._perf_bin,
                events=events,
                remove_absent_event=remove_absent_event,
            )

        self._events = events
        self._freq = freq
        self._quiet = quiet
        self._output_filename = output_filename
        self._use_json = use_json
        self._separator = separator  # if None, does not use `-x` option
        self._aggregate_hybrid = aggregate_hybrid

        self._perf_stat_options = None

    @property
    def perf_stat_options(self) -> List[str]:
        """Get all options formatted for the command line format of perf stat.

        Returns:
            List[str]: partial split command with all configured options.
        """
        if self._perf_stat_options is None:
            pro = []
            if self._events is not None:
                pro.extend(["-e", f"{','.join(self._events)}"])
            if self._freq is not None:
                pro.extend(["-I", f"{self._freq}"])
            if self._quiet:
                pro.append("--quiet")
            if self._use_json:
                pro.append("--json")
            elif self._separator is not None:
                # TODO We have to break the abstraction here, because sanitize only work for remote
                # We might want to find a better way to pass command to ssh and other remote
                # mechanisms in the future.
                if self.platform.comm.is_local:
                    pro.append(f"-x{self._separator}")
                else:
                    pro.append(f"-x'{self._separator}'")
            self._perf_stat_options = pro
        return self._perf_stat_options

    @staticmethod
    def _every_thread_cleanup(record_data_dir: pathlib.Path) -> None:
        for filename in os.listdir(record_data_dir):
            filename = str(filename)
            if filename.startswith("perf-stat-") and filename.endswith(".txt"):
                pathname = record_data_dir / filename
                if 0 == os.path.getsize(pathname):
                    os.remove(pathname)

    def dependencies(self) -> List[PackageDependency]:
        kernel_version = self.platform.kernel_version()
        return super().dependencies() + [
            PackageDependency("linux-tools-common"),
            PackageDependency("linux-tools-generic"),
            PackageDependency(f"linux-tools-{kernel_version}"),
        ]

    def command_prefix(  # pylint: disable=arguments-differ
        self,
        perf_stat_enable: bool = True,
        record_data_dir: Optional[PathType] = None,
        **kwargs,
    ) -> List[str]:
        """Define perf-stat prefix for the command to wrap.

        Args:
            perf_stat_enable (bool, optional): whether to enable the perf-stat prefix. Defaults to
                                               True.
            record_data_dir (Optional[PathType], optional): path to the record data directory if it
                                                            exists. Defaults to None.

        Returns:
            List[str]: _description_
        """
        cmd_prefix = super().command_prefix(**kwargs)

        if not perf_stat_enable:
            return cmd_prefix

        output_option = []
        if self._output_filename is not None:
            _validate_record_data_dir(record_data_dir=record_data_dir)
            perf_stat_pathname = os.path.join(record_data_dir, self._output_filename)
            output_option = ["--output", perf_stat_pathname]

        perf_prefix = _perf_command_prefix(perf_bin=self._perf_bin, platform=self.platform)
        cmd_prefix = perf_prefix + ["stat"] + self.perf_stat_options + output_option + cmd_prefix

        return cmd_prefix

    def updated_environment(self, environment: Environment) -> Environment:
        # Force locale to avoid confusion with "," and "." in json output:
        return environment | {"LC_NUMERIC": "en_US.UTF-8"}

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
            current_tids = ps.get_threads_of_process(pid=process.pid)
            for tid in current_tids:
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

    def post_run_hook_update_results(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        """
        Post run hook to generate extension to record results dict with the captured perf values.
        """
        assert experiment_results_lines  # to remove the "unused" warning
        assert write_record_file_fun  # to remove the "unused" warning

        # version without --per-thread
        global_perf_stat_pathname = os.path.join(record_data_dir, self._output_filename)

        # version with --per-thread
        output_filename_prefix = "perf-stat-"
        perf_stat_pathnames = sorted(
            [global_perf_stat_pathname]
            + [
                os.path.join(record_data_dir, f)
                for f in os.listdir(record_data_dir)
                if f.startswith(output_filename_prefix)
            ]
        )

        output_dict = {}
        for perf_stat_pathname in perf_stat_pathnames:
            if not os.path.exists(perf_stat_pathname):
                continue
            if "err-tid" in perf_stat_pathname:
                continue
            if "val-tid" in perf_stat_pathname:
                output_dict |= self._results_per_thread(perf_stat_pathname=perf_stat_pathname)
            else:
                output_dict |= self._results_global(perf_stat_pathname=perf_stat_pathname)

        if self._aggregate_hybrid:
            aggregate_hybrid_results(output_dict)

        return output_dict

    def _align_field_names(
        self,
        perf_stat_pathname: PathType,
        events: List[str],
        field_names: List[str],
    ) -> Optional[List[str]]:
        # For reasons beyond my understanding, perf stat returns a CSV file format that contains
        # optional fields without giving you the header of the file. To combat this, we try to
        # align the fields that are guaranteed to be given (given in field_names)
        # with the real CSV fields by inserting some padding to fill the optional fields if they
        # exist. We do this by trying to infer the location of the "event_name" column, we can
        # then align the field_names to that. Inferring this location is as easy as trying to
        # find the name of an event we were looking for in the row, since the event_name column
        # should contain the name of one of these events.
        with open(perf_stat_pathname, "r") as perf_stat_file:
            first_line_filter = filter(
                lambda row: not row.strip().startswith("#") and row.strip() != "",
                perf_stat_file,
            )
            row = next(first_line_filter, None)
            if row is None:
                return None
            fields = row.split(self._separator)

            event_idxes = [fields.index(event) for event in events if event in fields]

            # If we did not find an event in the row, we return the field names as we got
            # them because we cannot align the fields.
            if len(event_idxes) == 0:
                return field_names

            # We take the lowest index of the event indexes. In practice we should
            # only ever find one index here, but in theory it is possible that one
            # of the other fields (maybe a comment field) in the CSV contains a string
            # that matches the event name.
            idx_in_row = sorted(event_idxes)[0]
            idx_in_fieldnames = field_names.index("event")
            padding_events = [f"bogus-column{i}" for i in range(idx_in_row - idx_in_fieldnames)]
            return [*padding_events, *field_names]

    def _parse(
        self,
        perf_stat_pathname: PathType,
        field_names: List[str],
    ) -> List[Dict[str, str]]:
        if self._use_json:
            return self._parse_json(perf_stat_pathname=perf_stat_pathname, field_names=field_names)
        else:
            return self._parse_csv(perf_stat_pathname=perf_stat_pathname, field_names=field_names)

    def _parse_json(
        self,
        perf_stat_pathname: PathType,
        field_names: List[str],
    ) -> List[Dict[str, str]]:
        with open(perf_stat_pathname, "r") as perf_stat_file:
            lines = [line.strip() for line in perf_stat_file]
        json_lines = [json.loads(line) for line in lines]
        return json_lines

    def _parse_csv(
        self,
        perf_stat_pathname: PathType,
        field_names: List[str],
    ) -> List[Dict[str, str]]:
        field_names = self._align_field_names(
            perf_stat_pathname=perf_stat_pathname,
            events=self._events,
            field_names=field_names,
        )

        if field_names is None:
            return []

        with open(perf_stat_pathname, "r") as perf_stat_file:
            comments_filtered_file = filter(
                lambda row: not row.strip().startswith("#"),
                perf_stat_file,
            )
            reader = csv.DictReader(
                comments_filtered_file,
                fieldnames=field_names,
                delimiter=self._separator,
            )
            rows = [dict(row) for row in reader]

        return rows

    def _results_per_thread(
        self,
        perf_stat_pathname: PathType,
    ) -> RecordResult:

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

            event_name = counter_row["event_name"]
            if event_name.endswith("/"):
                event_name = event_name[:-1]
            counter_value = counter_row["counter_value"]
            unit = counter_row["counter_unit"]
            run_time = counter_row["run_time"]
            coverage = counter_row["percentage_counter_cover"]

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


class PerfReportWrap(CommandWrapper):
    """Command wrapper for the `perf record`/`perf report` utility."""

    def __init__(
        self,
        perf_path: Optional[PathType] = None,
        report_file: bool = True,
        report_interactive: bool = True,
        record_stack_traces: bool = True,
        freq: Optional[int] = None,
        call_graph: Optional[str] = "dwarf",
        stdio: bool = False,
        flamegraph_path: Optional[PathType] = None,
        perf_record_options: Optional[List[str]] = None,
        perf_report_options: Optional[List[str]] = None,
        platform: Platform | None = None,
    ):
        super().__init__()
        self.platform = get_current_platform() if platform is None else platform
        self.latest_perf_path = None

        self._perf_bin = _find_perf_bin(search_path=perf_path)

        self._report_file = report_file
        self._report_interactive = report_interactive
        self._record_stack_traces = record_stack_traces
        self._freq = freq
        self._call_graph = call_graph
        self._stdio = stdio
        self._flamegraph_path = flamegraph_path

        self._perf_record_options = perf_record_options
        self._perf_report_options = perf_report_options

    @property
    def perf_record_options(self) -> List[str]:
        """Get all options formatted for the command line format of perf record.

        Returns:
            List[str]: partial split commands with the options formatted as expected by perf-record
                       command line.
        """
        if self._perf_record_options is None:
            pro = []
            if self._freq is not None:
                pro.extend(["-F", f"{self._freq}"])
            if self._call_graph is not None:
                pro.extend(["--call-graph", f"{self._call_graph}"])
            if self._record_stack_traces:
                pro.extend(["-g"])
            self._perf_record_options = pro
        return self._perf_record_options

    @property
    def perf_report_options(self) -> List[str]:
        """Get all options formatted for the command line format of perf report.

        Returns:
            List[str]: partial split commands with the options formatted as expected by perf-report
                       command line.
        """
        if self._perf_report_options is None:
            pro = []
            if self._call_graph is not None:
                pro.extend(["--call-graph", "-G"])
            if self._stdio:
                pro.append("--stdio")
            self._perf_report_options = pro
        return self._perf_report_options

    def dependencies(self) -> List[PackageDependency]:
        kernel_version = self.platform.kernel_version()
        return super().dependencies() + [
            PackageDependency("fzf"),
            PackageDependency("linux-tools-common"),
            PackageDependency("linux-tools-generic"),
            PackageDependency(f"linux-tools-{kernel_version}"),
            PackageDependency("util-linux"),  # for fzf
        ]

    def command_prefix(  # pylint: disable=arguments-differ
        self,
        record_data_dir: Optional[PathType],
        **kwargs,
    ) -> List[str]:
        cmd_prefix = super().command_prefix(**kwargs)

        _validate_record_data_dir(record_data_dir=record_data_dir)
        perf_data_pathname = os.path.join(record_data_dir, "perf.data")

        perf_prefix = _perf_command_prefix(perf_bin=self._perf_bin, platform=self.platform)
        cmd_prefix = (
            perf_prefix
            + ["record", "--output", f"{perf_data_pathname}"]
            + self.perf_record_options
            + cmd_prefix
        )

        self.latest_perf_path = perf_data_pathname

        return cmd_prefix

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

        command = self._perf_report_command(perf_data_pathname=perf_data_pathname)

        # retrieve output into file first for posterity
        if self._report_file:
            file_command = command + ([] if self._stdio else ["--stdio"])
            output = shell_out(file_command, print_output=False)

            write_record_file_fun(file_content=output.strip(), filename="perf.report")

        if self._report_interactive:
            shell_interactive(command=command, ignore_ret_codes=(-13,))  # ignore broken pipe error

    def fetch_flamegraph(
        self,
        flamegraph_commit: str = "41fee1f99f9276008b7cd112fca19dc3ea84ac32",
    ) -> None:
        if self._flamegraph_path.is_dir():
            return

        # Cannot use fetchtools.git_clone as there is no context.
        parent_dir = self._flamegraph_path.parent.resolve()
        flamegraph_url = "https://github.com/brendangregg/FlameGraph.git"

        self.platform.comm.makedirs(path=parent_dir, exist_ok=True)

        self.platform.comm.shell(
            command=["git", "clone", f"{flamegraph_url}", "FlameGraph"],
            current_dir=parent_dir,
        )
        self.platform.comm.shell(
            command=["git", "checkout", f"{flamegraph_commit}"],
            current_dir=parent_dir / "FlameGraph",
        )

    def post_run_hook_flamegraph(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
        flamegraph_title: str = "",
        flamegraph_subtitle: str = "",
        flamegraph_width: int | None = None,
        flamegraph_height: int | None = None,
        flamegraph_fontsize: int | None = None,
        flamegraph_minwidth: float | None = None,
    ) -> None:
        """Post run hook to generate flamegraph into data directory of the record.

        Raises:
            PerfWrapError: when flamegraph path has not been given at wrapper creation.
        """
        assert experiment_results_lines and record_data_dir  # ignore unused

        if self._flamegraph_path is None:
            raise PerfWrapError(
                (
                    "Trying to generate flamegraph on post "
                    "run hook but flamegraph_path not provided "
                    "to perf wrapper instance."
                )
            )

        perf_data_pathname = self.latest_perf_path
        perf_data_dirname = pathlib.Path(self.latest_perf_path).parent.resolve()
        perf_folded_pathname = perf_data_dirname / "perf.folded"

        self._chown(pathname=perf_data_pathname)

        out_perf = shell_out(
            f"{self._perf_bin} script --input {perf_data_pathname}",
            print_output=False,
        )

        flamegraph_path = os.path.realpath(self._flamegraph_path)
        stackcollperf_script = os.path.join(flamegraph_path, "stackcollapse-perf.pl")
        out_folded = shell_out(
            stackcollperf_script,
            std_input=out_perf,
            current_dir=flamegraph_path,
            print_output=False,
        )
        perf_folded_pathname.write_text(out_folded.strip())

        flamegraph_command = self._flamegraph_command(
            title=flamegraph_title,
            subtitle=flamegraph_subtitle,
            width=flamegraph_width,
            height=flamegraph_height,
            fontsize=flamegraph_fontsize,
            minwidth=flamegraph_minwidth,
        )

        svg_flamechart = shell_out(
            command=flamegraph_command,
            std_input=out_folded,
            current_dir=flamegraph_path,
            print_output=False,
        )

        write_record_file_fun(file_content=svg_flamechart, filename=FILENAME_FLAMEGRAPH)

    def differential_flamegraph(
        self,
        src_folded_path: PathType,
        dst_folded_path: PathType,
        out_svg_path: PathType,
        flamegraph_title: str = "",
        flamegraph_subtitle: str = "",
        flamegraph_width: int | None = None,
        flamegraph_height: int | None = None,
        flamegraph_fontsize: int | None = None,
        flamegraph_minwidth: float | None = None,
    ) -> None:
        flamegraph_path = pathlib.Path(self._flamegraph_path)
        src_folded_path = pathlib.Path(src_folded_path).resolve()
        dst_folded_path = pathlib.Path(dst_folded_path).resolve()
        out_svg_path = pathlib.Path(out_svg_path).resolve()
        if not all(f.exists() for f in [flamegraph_path, src_folded_path, dst_folded_path]):
            raise ValueError("Cannot find all folded files.")

        difffolded_out = self.platform.comm.shell(
            command=[
                "./difffolded.pl",
                f"{src_folded_path}",
                f"{dst_folded_path}",
            ],
            current_dir=flamegraph_path,
        )

        flamegraph_command = self._flamegraph_command(
            title=flamegraph_title,
            subtitle=flamegraph_subtitle,
            width=flamegraph_width,
            height=flamegraph_height,
            fontsize=flamegraph_fontsize,
            minwidth=flamegraph_minwidth,
        )

        svg_diffflamechart = self.platform.comm.shell(
            command=flamegraph_command,
            std_input=difffolded_out,
            current_dir=flamegraph_path,
            print_output=False,
        )
        out_svg_path.write_text(svg_diffflamechart)

    def fzf_report(self, search_dir: PathType) -> None:
        """Generate all report browsable with fzf dynamic CLI.

        Args:
            search_dir (PathType): path where to look for the perf report files.
        """
        self._fzf(
            search_dir=search_dir,
            target_filename="perf.data",
            header="perf report?",
            command_fun=lambda path: self._perf_report_command(perf_data_pathname=path),
        )

    def fzf_flamegraph(self, search_dir: PathType) -> None:
        """Generate all flamegraphs browsable with fzf dynamic CLI.

        Args:
            search_dir (PathType): path where to look for the flamegraph files.
        """

        def open_browser(arg: PathType):
            command = f"python3 -m webbrowser {arg}"
            result = command.split(" ")
            return result

        self._fzf(
            search_dir=search_dir,
            target_filename=FILENAME_FLAMEGRAPH,
            header="flamegraph?",
            command_fun=open_browser,
        )

    def _flamegraph_command(
        self,
        title: str = "",
        subtitle: str = "",
        width: int | None = None,
        height: int | None = None,
        fontsize: int | None = None,
        minwidth: float | None = None,
    ) -> List[str]:
        flamegraph_path = pathlib.Path(self._flamegraph_path).resolve()
        script = flamegraph_path / "flamegraph.pl"

        command = [f"{script}"]
        if title:
            command.append(f"--title={title}")
        if subtitle:
            command.append(f"--subtitle={subtitle}")
        if width is not None:
            command.append(f"--width={width}")
        if height is not None:
            command.append(f"--height={height}")
        if fontsize is not None:
            command.append(f"--fontsize={fontsize}")
        if minwidth is not None:
            command.append(f"--minwidth={minwidth}")

        return command

    def _chown(self, pathname: PathType) -> None:
        path = pathlib.Path(pathname)
        current_owner = path.owner()  # TODO only works on local platforms
        user = self.platform.current_user()
        if current_owner != user:
            shell_out(["sudo", "chown", f"{user}:{user}", str(path)], print_output=False)

    def _perf_report_command(self, perf_data_pathname: PathType) -> SplitCommand:
        command = [
            self._perf_bin,
            "report",
            "--input",
            f"{perf_data_pathname}",
        ] + self.perf_report_options

        return command

    def _fzf(
        self,
        search_dir: PathType,
        target_filename: str,
        header: str,
        command_fun: Callable[[PathType], SplitCommand],
    ):
        paths = [
            f
            for f in _find(find_dir=search_dir, include_subdirs=False)
            if f.endswith(target_filename)
        ]
        files = [os.path.relpath(f, search_dir) for f in paths]

        for path in paths:
            self._chown(pathname=path)

        while chosen_file := shell_out(
            command=["fzf", "--header", header],
            std_input="\n".join(files),
            ignore_ret_codes=(130,),  # ignore pipe broken
        ).strip():
            chosen_path = os.path.join(search_dir, chosen_file)
            command = command_fun(chosen_path)
            shell_interactive(command=command, ignore_ret_codes=(-13,))  # ignore broken pipe error


def aggregate_hybrid_results(perf_results: dict[str, str | int]) -> None:
    def _parse_num(v: Any) -> Optional[float]:
        """
        Parse perf stat numeric field:
          - "8008.000000" -> 8008.0
          - "<not counted>" / None / "" -> None
        """
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if not s or s.startswith("<"):
            return None
        # perf sometimes uses commas depending on locale; be conservative
        s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    def _get_triplet(
        d: dict,
        k: str,
    ) -> Tuple[Optional[float], str, Optional[float], Optional[float]]:
        """
        Returns (value, unit, rt, cov) for base key k.
        """
        val = _parse_num(d.get(k))
        unit = str(d.get(f"{k}.unit") or "")
        rt = _parse_num(d.get(f"{k}.rt"))
        cov = _parse_num(d.get(f"{k}.cov"))
        return val, unit, rt, cov

    def _fmt_value(x: float) -> str:
        # keep same style as perf stat parsing typically yields
        return f"{x:.6f}"

    def _fmt_int_like(x: float) -> int:
        return int(round(x))

    def _fmt_cov(x: float) -> str:
        return f"{x:.1f}"

    # Recognize hybrid PMU prefixes to merge.
    pmu_prefixes = ("cpu_atom", "cpu_core")

    # Build set of "event base names" that exist for at least one PMU.
    # Example: perf-stat/cpu_atom/cache-misses -> event = cache-misses
    event_re = re.compile(r"^perf-stat/(%s)/(.+)$" % "|".join(map(re.escape, pmu_prefixes)))

    events: set[str] = set()
    for k in perf_results.keys():
        # ignore metadata suffixes here; we’ll handle them via base keys
        if k.endswith((".unit", ".rt", ".cov")):
            continue
        m = event_re.match(k)
        if m:
            events.add(m.group(2))

    for event in sorted(events):
        agg_key = f"perf-stat/{event}"

        total = 0.0
        any_counted = False

        # For unit: pick first non-empty (they should match anyway)
        unit_out = ""

        # For rt/cov: compute a weighted cov by rt when possible, else fall back.
        rt_sum = 0.0
        cov_weighted_sum = 0.0
        cov_fallback = 0.0
        rt_fallback = 0.0

        for pmu in pmu_prefixes:
            base = f"perf-stat/{pmu}/{event}"
            val, unit, rt, cov = _get_triplet(perf_results, base)

            if unit and not unit_out:
                unit_out = unit

            if val is not None:
                total += val
                any_counted = True

            # rt/cov handling
            if rt is not None and rt > 0:
                rt_sum += rt
                if cov is not None:
                    cov_weighted_sum += cov * rt
            else:
                # keep best-effort fallback (e.g. atom has rt, core has 0)
                if rt is not None:
                    rt_fallback = max(rt_fallback, rt)
                if cov is not None:
                    cov_fallback = max(cov_fallback, cov)

        if any_counted:
            perf_results[agg_key] = _fmt_value(total)
        else:
            # if neither PMU counted, keep the canonical "<not counted>"
            perf_results[agg_key] = "<not counted>"

        # unit
        perf_results[f"{agg_key}.unit"] = unit_out

        # rt: prefer sum of non-zero rts (system-wide style), else fallback
        rt_out = rt_sum if rt_sum > 0 else rt_fallback
        perf_results[f"{agg_key}.rt"] = _fmt_int_like(rt_out)

        # cov: prefer weighted average by rt, else fallback, else 0.0
        if rt_sum > 0 and cov_weighted_sum > 0:
            cov_out = cov_weighted_sum / rt_sum
        else:
            cov_out = cov_fallback
        perf_results[f"{agg_key}.cov"] = _fmt_cov(cov_out)
