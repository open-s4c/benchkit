# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Tests of the record generators and their wiring into campaigns.

These tests guard the Phase-1 extraction: exploration is described by a
RecordGenerator, while the campaigns keep materializing the records at
construction time exactly as before.
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from benchkit.campaign import CampaignCartesianProduct, CampaignIterateVariables, CampaignTemplate
from benchkit.engine.generators import CartesianGenerator, FilteredGenerator, ListGenerator
from benchkit.utils.variables import cartesian_product
from tests.engine.test_execution import EchoBench

_VARIABLES = {"message": ["hello", "world"], "other": [1, 2]}


class TestGenerators(unittest.TestCase):
    """Unit tests of the generator implementations."""

    def test_cartesian_generator_matches_cartesian_product(self) -> None:
        generator = CartesianGenerator(variables=_VARIABLES)
        self.assertEqual(list(cartesian_product(_VARIABLES)), list(generator.records()))

    def test_cartesian_generator_is_reiterable(self) -> None:
        generator = CartesianGenerator(variables={"message": iter(["hello", "world"])})
        first = list(generator.records())
        second = list(generator.records())
        self.assertEqual(first, second)
        self.assertEqual(2, len(first))

    def test_list_generator_preserves_records(self) -> None:
        records = [{"message": "world"}, {"message": "hello"}]
        generator = ListGenerator(records=records)
        self.assertEqual(records, list(generator.records()))

    def test_list_generator_is_reiterable(self) -> None:
        generator = ListGenerator(records=iter([{"message": "hello"}]))
        self.assertEqual(list(generator.records()), list(generator.records()))

    def test_filtered_generator_filters_and_preserves_order(self) -> None:
        generator = FilteredGenerator(
            generator=CartesianGenerator(variables=_VARIABLES),
            predicate=lambda record: record["other"] == 2,
        )
        expected = [r for r in cartesian_product(_VARIABLES) if r["other"] == 2]
        self.assertEqual(expected, list(generator.records()))

    def test_filtered_generator_is_reiterable(self) -> None:
        generator = FilteredGenerator(
            generator=ListGenerator(records=[{"message": "hello"}, {"message": "world"}]),
            predicate=lambda record: record["message"] == "hello",
        )
        first = list(generator.records())
        self.assertEqual(first, list(generator.records()))
        self.assertEqual([{"message": "hello"}], first)


class TestCampaignGeneratorWiring(unittest.TestCase):
    """Check that campaigns build and expose the expected generators."""

    @staticmethod
    def _template_kwargs(results_dir: Path) -> Dict[str, Any]:
        return {
            "name": "generatorsmoke",
            "benchmark": EchoBench(),
            "nb_runs": 1,
            "constants": None,
            "debug": False,
            "gdb": False,
            "enable_data_dir": True,
            "continuing": False,
            "results_dir": results_dir,
        }

    def test_template_requires_exactly_one_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                CampaignTemplate(
                    variables=None,
                    record_generator=None,
                    **self._template_kwargs(results_dir=Path(tmp)),
                )
            with self.assertRaises(ValueError):
                CampaignTemplate(
                    variables=[{"message": "hello"}],
                    record_generator=ListGenerator(records=[{"message": "hello"}]),
                    **self._template_kwargs(results_dir=Path(tmp)),
                )

    def test_cartesian_campaign_exposes_cartesian_generator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            campaign = CampaignCartesianProduct(
                name="generatorsmoke",
                benchmark=EchoBench(),
                nb_runs=1,
                variables=_VARIABLES,
                constants=None,
                debug=False,
                gdb=False,
                enable_data_dir=True,
                results_dir=Path(tmp),
            )
            self.assertIsInstance(campaign.record_generator, CartesianGenerator)
            self.assertEqual(list(cartesian_product(_VARIABLES)), campaign.parameters["variables"])

    def test_filtered_cartesian_campaign_keeps_legacy_records(self) -> None:
        def keep(record: Dict[str, Any]) -> bool:
            return record["message"] == "hello"

        with tempfile.TemporaryDirectory() as tmp:
            campaign = CampaignCartesianProduct(
                name="generatorsmoke",
                benchmark=EchoBench(),
                nb_runs=1,
                variables=_VARIABLES,
                constants=None,
                debug=False,
                gdb=False,
                enable_data_dir=True,
                results_dir=Path(tmp),
                filter_func=keep,
            )
            expected = [r for r in cartesian_product(_VARIABLES) if keep(r)]
            self.assertIsInstance(campaign.record_generator, FilteredGenerator)
            self.assertEqual(expected, campaign.parameters["variables"])

    def test_iterate_campaign_gets_list_generator(self) -> None:
        records = [{"message": "world"}, {"message": "hello"}]
        with tempfile.TemporaryDirectory() as tmp:
            campaign = CampaignIterateVariables(
                name="generatorsmoke",
                benchmark=EchoBench(),
                nb_runs=1,
                variables=records,
                constants=None,
                debug=False,
                gdb=False,
                enable_data_dir=True,
                results_dir=Path(tmp),
            )
            self.assertIsInstance(campaign.record_generator, ListGenerator)
            self.assertEqual(records, campaign.parameters["variables"])


class TestExplicitGeneratorEndToEnd(unittest.TestCase):
    """Run a campaign built from an explicit CartesianGenerator end-to-end."""

    @staticmethod
    def _csv_data_lines(csv_path: Path) -> List[str]:
        lines = [line.strip() for line in csv_path.read_text().splitlines()]
        return [line for line in lines if line and not line.startswith("#")]

    def test_campaign_with_explicit_generator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            campaign = CampaignTemplate(
                variables=None,
                record_generator=CartesianGenerator(variables={"message": ["hello", "world"]}),
                **TestCampaignGeneratorWiring._template_kwargs(results_dir=Path(tmp)),
            )
            campaign.run()

            csv_path = Path(campaign.parameters["result_csv_path"])
            self.assertTrue(csv_path.is_file())

            data_lines = self._csv_data_lines(csv_path)
            header, rows = data_lines[0], data_lines[1:]
            self.assertIn("input/message", header.split(";"))
            self.assertEqual(2, len(rows))  # 2 variable values x 1 run


if __name__ == "__main__":
    unittest.main()
