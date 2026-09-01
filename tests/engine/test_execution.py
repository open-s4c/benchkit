# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
End-to-end tests of campaign execution through the ExecutionEngine.

These tests guard the Phase-1 delegation: legacy `Campaign*` classes keep
their behavior but route orchestration through `ExecutionEngine`.
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from benchkit.benchmark import Benchmark
from benchkit.campaign import CampaignCartesianProduct
from benchkit.engine.execution import ExecutionEngine
from benchkit.utils.dir import caller_dir


class EchoBench(Benchmark):
    """Minimal legacy benchmark echoing its single run variable."""

    def __init__(self) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=(),
        )

    @property
    def bench_src_path(self) -> Path:
        return caller_dir()

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return ["message"]

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        message: str,
        **kwargs,
    ) -> str:
        environment = self._preload_env(message=message, **kwargs)

        run_command = ["echo", message]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            message=message,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self.bench_src_path,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
        return {"echoed": command_output.strip()}


class TestExecutionEngine(unittest.TestCase):
    """Run a tiny campaign end-to-end and check the produced CSV."""

    @staticmethod
    def _make_campaign(results_dir: Path) -> CampaignCartesianProduct:
        return CampaignCartesianProduct(
            name="enginesmoke",
            benchmark=EchoBench(),
            nb_runs=2,
            variables={"message": ["hello", "world"]},
            constants=None,
            debug=False,
            gdb=False,
            enable_data_dir=False,
            results_dir=results_dir,
        )

    @staticmethod
    def _csv_data_lines(csv_path: Path) -> List[str]:
        lines = [line.strip() for line in csv_path.read_text().splitlines()]
        return [line for line in lines if line and not line.startswith("#")]

    def _check_csv(self, campaign: CampaignCartesianProduct) -> None:
        csv_path = Path(campaign.parameters["result_csv_path"])
        self.assertTrue(csv_path.is_file())

        data_lines = self._csv_data_lines(csv_path)
        header, rows = data_lines[0], data_lines[1:]

        self.assertIn("message", header.split(";"))
        self.assertIn("echoed", header.split(";"))
        self.assertEqual(4, len(rows))  # 2 variable values x 2 runs

        message_idx = header.split(";").index("message")
        echoed_idx = header.split(";").index("echoed")
        for row in rows:
            fields = row.split(";")
            self.assertEqual(fields[message_idx], fields[echoed_idx])

    def test_campaign_run_through_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            campaign = self._make_campaign(results_dir=Path(tmp))
            campaign.run()
            self._check_csv(campaign=campaign)

    def test_engine_run_direct(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            campaign = self._make_campaign(results_dir=Path(tmp))
            engine = ExecutionEngine()
            engine.run(campaign=campaign)
            self._check_csv(campaign=campaign)


if __name__ == "__main__":
    unittest.main()
