# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import re
from collections import defaultdict
from threading import Thread
from typing import Any, Dict, List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.commandwrappers.perf import PerfStatWrap
from benchkit.utils.types import PathType


class CPIPerfStatWrap(PerfStatWrap):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_run_stats = {}

    def attachment(self, **kwargs):
        self.attachment_thread = Thread(target=self.attach_every_thread, kwargs=kwargs)
        self.attachment_thread.start()

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ):
        assert self.attachment_thread is not None
        self.attachment_thread.join()

        output_filename_prefix = "perf-stat-"
        perf_stat_pathnames = sorted(
            [
                os.path.join(record_data_dir, f)
                for f in os.listdir(record_data_dir)
                if f.startswith(output_filename_prefix)
            ]
        )

        tid_re = re.compile(r"^.*-(\d+).*$")

        per_tid_counters: dict[int, dict] = defaultdict(lambda: {})

        # output_dict = {}
        for perf_stat_pathname in perf_stat_pathnames:
            if not os.path.exists(perf_stat_pathname):
                continue
            if "err-tid" in perf_stat_pathname:
                continue
            if "val-tid" in perf_stat_pathname:
                counter_stats: List[Dict[str, Any]] = self._parse_json(
                    perf_stat_pathname=perf_stat_pathname,
                    field_names=["taskname-pid"] + self._perf_stat_csv_field_names,
                )

                for counter_stat in counter_stats:
                    tid_m = tid_re.search(counter_stat["thread"])
                    if tid_m:
                        tid = int(tid_m.group(1))
                    else:
                        raise RuntimeError(
                            "CPIPerfStatWrap encounterd a thread name that could not be parsed"
                        )

                    counter_stat["tid"] = tid
                    per_tid_counters[tid][counter_stat["event"]] = float(
                        counter_stat["counter-value"]
                    )

        for tid, counters in per_tid_counters.items():
            if all(event in counters for event in ["cycles", "instructions"]):
                counters["cpi"] = counters["cycles"] / counters["instructions"]
            else:
                raise RuntimeError(
                    "CPIPerfStatWrap per_tid_counters did not contain either cycles or instructions"
                )

        self._current_run_stats = per_tid_counters
        return {}

    def get_current_run_stats(self):
        return self._current_run_stats
