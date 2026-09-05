# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Tests of the execution policies.

SequentialPolicy is the current behavior formalized: these tests guard that
an engine composed with an explicit policy runs a campaign end-to-end
exactly like the default construction path.
"""

import tempfile
import unittest
from pathlib import Path
from typing import List

from benchkit.campaign import CampaignCartesianProduct
from benchkit.engine.execution import ExecutionEngine
from benchkit.engine.policies import SequentialPolicy
from tests.engine.test_execution import EchoBench


class TestSequentialPolicy(unittest.TestCase):
    @staticmethod
    def _make_campaign(results_dir: Path) -> CampaignCartesianProduct:
        return CampaignCartesianProduct(
            name="policysmoke",
            benchmark=EchoBench(),
            nb_runs=2,
            variables={"message": ["hello", "world"]},
            constants=None,
            debug=False,
            gdb=False,
            enable_data_dir=True,
            results_dir=results_dir,
        )

    @staticmethod
    def _csv_data_lines(csv_path: Path) -> List[str]:
        lines = [line.strip() for line in csv_path.read_text().splitlines()]
        return [line for line in lines if line and not line.startswith("#")]

    def test_default_engine_policy_is_sequential(self) -> None:
        engine = ExecutionEngine()
        self.assertIsInstance(engine.policy, SequentialPolicy)

    def test_explicit_policy_is_kept(self) -> None:
        policy = SequentialPolicy()
        engine = ExecutionEngine(policy=policy)
        self.assertIs(policy, engine.policy)

    def test_engine_with_explicit_sequential_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            campaign = self._make_campaign(results_dir=Path(tmp))
            engine = ExecutionEngine(policy=SequentialPolicy())
            engine.run(campaign=campaign)

            csv_path = Path(campaign.parameters["result_csv_path"])
            self.assertTrue(csv_path.is_file())

            data_lines = self._csv_data_lines(csv_path)
            header, rows = data_lines[0], data_lines[1:]
            columns = header.split(";")
            self.assertIn("input/message", columns)
            self.assertIn("output/echoed", columns)
            self.assertEqual(4, len(rows))  # 2 variable values x 2 runs

            message_idx = columns.index("input/message")
            echoed_idx = columns.index("output/echoed")
            for row in rows:
                fields = row.split(";")
                self.assertEqual(fields[message_idx], fields[echoed_idx])


if __name__ == "__main__":
    unittest.main()
