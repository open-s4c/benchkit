# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from typing import List, Optional

from benchkit.benches.leveldb import LevelDBBench
from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.core.compat.new2old import CampaignCartesianProduct
from benchkit.utils.types import PathType


def prerun_hook(
    build_variables: RecordResult,
    run_variables: RecordResult,
    other_variables: RecordResult,
    record_data_dir: PathType,
) -> None:
    if record_data_dir:
        trace = record_data_dir / "trace.txt"
        trace.write_text(
            f"Record for:\n  {build_variables}\n  {run_variables}\n  {other_variables}\n"
        )


def postrun_hook(
    experiment_results_lines: List[RecordResult],
    record_data_dir: PathType,
    write_record_file_fun: WriteRecordFileFunction,
) -> Optional[RecordResult]:
    path = record_data_dir / "results.txt"
    write_record_file_fun(file_content=f"Results:\n  {experiment_results_lines[-1]}", filename=path)
    return {"path": f"{path}"}


def main() -> None:
    parameter_space = {
        "bench_name": ["readrandom", "seekrandom"],
        "nb_threads": [2, 4, 8],
    }

    campaign = CampaignCartesianProduct(
        benchmark=LevelDBBench(),
        parameter_space=parameter_space,
        pre_run_hooks=[prerun_hook],
        post_run_hooks=[postrun_hook],
    )

    campaign.run()

    campaign.generate_graph(
        plot_name="lineplot",
        x="nb_threads",
        y="throughput",
        hue="bench_name",
    )


if __name__ == "__main__":
    main()
