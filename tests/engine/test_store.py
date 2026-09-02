# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Tests of the result stores: CSV journal, JSON metadata & records, composite.
"""

import json
import tempfile
import unittest
from pathlib import Path
from typing import List

from benchkit.engine.stores import CsvJsonStore, CsvStore, JsonStore, strip_role


def _csv_lines(csv_path: Path) -> List[str]:
    return [line for line in csv_path.read_text().splitlines() if line.strip()]


class TestStripRole(unittest.TestCase):
    def test_strip_role(self) -> None:
        self.assertEqual("nb_threads", strip_role("input/nb_threads"))
        self.assertEqual("throughput", strip_role("output/throughput"))
        self.assertEqual("rep", strip_role("rep"))
        self.assertEqual("path/with/slash", strip_role("path/with/slash"))


class TestCsvStore(unittest.TestCase):
    @staticmethod
    def _write_one(store: CsvStore, message: str, rep: int = 1, extra: dict = None) -> None:
        store.write_record(
            identity={"experiment_name": "exp", "benchmark_name": "bench"},
            constants={"hostname": "host"},
            inputs={"message": message},
            rep=rep,
            outputs={"echoed": message, **(extra or {})},
        )

    def test_header_sections_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "out.csv"
            store = CsvStore(csv_output_path=csv_path)
            self._write_one(store, "hello")
            self._write_one(store, "world", rep=2)

            lines = _csv_lines(csv_path)
            self.assertEqual(
                "identity/experiment_name;identity/benchmark_name;constant/hostname;"
                "input/message;rep;output/echoed",
                lines[0],
            )
            self.assertEqual("exp;bench;host;hello;1;hello", lines[1])
            self.assertEqual("exp;bench;host;world;2;world", lines[2])

    def test_schema_growth_rewrites_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "out.csv"
            store = CsvStore(csv_output_path=csv_path)
            self._write_one(store, "hello")
            self._write_one(store, "world", extra={"latency": 42})

            lines = _csv_lines(csv_path)
            header = lines[0].split(";")
            self.assertIn("output/latency", header)
            # The early row is re-rendered against the extended header:
            first_row = dict(zip(header, lines[1].split(";")))
            self.assertEqual("", first_row["output/latency"])
            second_row = dict(zip(header, lines[2].split(";")))
            self.assertEqual("42", second_row["output/latency"])

    def test_existing_records_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "out.csv"
            store = CsvStore(csv_output_path=csv_path)
            self._write_one(store, "hello")

            resumed = CsvStore(csv_output_path=csv_path, continuing=True)
            records = resumed.existing_records()
            self.assertEqual(1, len(records))
            self.assertEqual("hello", records[0]["message"])
            self.assertEqual("hello", records[0]["echoed"])
            self.assertEqual("1", records[0]["rep"])

    def test_continuing_appends_without_rewriting_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "out.csv"
            store = CsvStore(csv_output_path=csv_path)
            self._write_one(store, "hello")
            header_before = _csv_lines(csv_path)[0]

            resumed = CsvStore(csv_output_path=csv_path, continuing=True)
            self._write_one(resumed, "world", rep=2)

            lines = _csv_lines(csv_path)
            self.assertEqual(header_before, lines[0])
            self.assertEqual(3, len(lines))  # header + 2 rows

    def test_pretty_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "out.csv"
            store = CsvStore(
                csv_output_path=csv_path,
                pretty_variables={"message": {"hello": "Hello, world!"}},
            )
            self._write_one(store, "hello")

            lines = _csv_lines(csv_path)
            header = lines[0].split(";")
            self.assertIn("pretty/message_pretty", header)
            row = dict(zip(header, lines[1].split(";")))
            self.assertEqual('"Hello, world!"', row["pretty/message_pretty"])


class TestJsonStore(unittest.TestCase):
    def test_metadata_written_and_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonStore(base_data_dir=tmp)
            store.begin(metadata={"benchmark_campaign_name": "exp", "nb_runs": 2})
            store.end(metadata={"total_duration_seconds": 1.5})

            metadata = json.loads((Path(tmp) / "metadata.json").read_text())
            self.assertEqual("exp", metadata["benchmark_campaign_name"])
            self.assertEqual(2, metadata["nb_runs"])
            self.assertEqual(1.5, metadata["total_duration_seconds"])

    def test_record_json_is_role_structured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record_dir = Path(tmp) / "record"
            record_dir.mkdir()
            store = JsonStore(base_data_dir=tmp)
            store.write_record(
                identity={"experiment_name": "exp", "benchmark_name": "bench"},
                constants={"hostname": "host"},
                inputs={"message": "hello"},
                rep=1,
                outputs={"echoed": "hello"},
                record_data_dir=record_dir,
            )

            record = json.loads((record_dir / "experiment_results.json").read_text())
            self.assertEqual({"message": "hello"}, record["inputs"])
            self.assertEqual({"echoed": "hello"}, record["outputs"])
            self.assertEqual(1, record["rep"])
            self.assertEqual("exp", record["identity"]["experiment_name"])


class TestCsvJsonStore(unittest.TestCase):
    def test_composite_writes_all_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "out.csv"
            record_dir = Path(tmp) / "record"
            record_dir.mkdir()
            store = CsvJsonStore(
                csv_output_path=csv_path,
                base_data_dir=tmp,
            )
            store.begin(metadata={"benchmark_campaign_name": "exp"})
            store.write_record(
                identity={"experiment_name": "exp", "benchmark_name": "bench"},
                constants={},
                inputs={"message": "hello"},
                rep=1,
                outputs={"echoed": "hello"},
                record_data_dir=record_dir,
            )
            store.end(metadata={"total_duration_seconds": 0.1})

            self.assertTrue(csv_path.is_file())
            self.assertTrue((Path(tmp) / "metadata.json").is_file())
            self.assertTrue((record_dir / "experiment_results.json").is_file())
            self.assertEqual(1, len(store.existing_records()))


if __name__ == "__main__":
    unittest.main()
