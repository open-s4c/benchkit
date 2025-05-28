# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from typing import List, Optional
from benchkit.benchmark import PostRunHook, PreRunHook, RecordResult, WriteRecordFileFunction
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import get_current_platform
from benchkit.shell.shellasync import shell_async
from benchkit.utils.types import PathType


class StressNgPreHook(PreRunHook):
    """
    Hook to start `stress-ng` as a stressor before your command.
    """

    def __init__(self, duration: int) -> None:
        """
        Create a new `stress-ng` pre-hook

        Args:
            duration (int):
                How long `stress-ng` should run for.
                NOTE: This should be the length that you want the stressor active, but `stress-ng` takes
                    some time after this to tear down all of the resources it has used.
                    Because of this you should also use the stress ng post hook to wait for `stress-ng` to finish
                    tearing down before starting a new experiment, this is called `StressNgPostHook`.
        """
        super().__init__()
        self._duration = duration
        self._platform = get_current_platform()

    def __call__(
        self,
        build_variables: RecordResult,
        run_variables: RecordResult,
        other_variables: RecordResult,
        record_data_dir: PathType,
    ) -> None:
        stress_ng_command = [
            "stress-ng",
            "--all",
            "1",
            "--timeout",
            f"{self._duration}s",
        ]
        pid = shell_async(
            command=stress_ng_command,
            stdout_path="/tmp/benchkit_stress_ng_stdout.txt",
            stderr_path="/tmp/benchkit_stress_ng_stderr.txt",
            platform=self._platform,
            # These error codes mean that some stressors failed, or failed to initialize, possibly because of lack of resources.
            # Since this command is a stressor, meaning that the system resources are used intensively, it is normal that they could get exhausted,
            # especially on large runs, and we don't want to stop the benchmark if this happens.
            ignore_ret_codes=[2, 3],
        )
        self._stress_ng_process = pid

    def stressNgProcess(self):
        """
        Returns the stress ng that is currently running.
        """
        return self._stress_ng_process


class StressNgPostHook(PostRunHook):
    """
    Hook to wait for `stress-ng` to finish its teardown before continuing to the next experiment.

    This hook will run after every experiment, and wait until the `stress-ng` process, spawned by the
    StressNgPreHook has finished.
    """

    def __init__(self, stressNgPreHook: StressNgPreHook) -> None:
        """
        Create a new `stress-ng` post hook

        Args:
            stressNgPreHook (StressNgPreHook):
                The stress-ng pre-hook that you are using to start `stress-ng`,
                this is necessary to get the `stress-ng` process.
        """
        super().__init__()
        self._stressNgPreHook = stressNgPreHook

    def __call__(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> Optional[RecordResult]:
        if self._stressNgPreHook.stressNgProcess() is None:
            return None

        self._stressNgPreHook.stressNgProcess().wait()
        return None
