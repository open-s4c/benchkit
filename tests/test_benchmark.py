# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module for testing the benchmark class.
"""

import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

from benchkit.benchmark import Benchmark, RecordResult
from benchkit.sharedlibs.tiltlib import TiltLib


class TiltMock(TiltLib):
    """Mock for tilt library."""

    def __init__(self) -> None:
        super().__init__(src_path="", debug_mode=False)

    def configure(self) -> None:
        print("[TILT] CONFIGURE")

    def clean(self) -> None:
        print("[TILT] CLEAN")

    def build_single_lock(self, **kwargs) -> None:  # pylint: disable=arguments-differ
        print("[TILT] BUILD", kwargs)

    def get_compiler(self) -> str:
        return "{TILT COMPILER}"

    def get_exact_compiler(self) -> str:
        return "{TILT EXACT COMPILER}"


class BenchmarkMock(Benchmark):
    """Mock for benchmark class implementation (derivation)."""

    def __init__(self, tilt):
        super().__init__(
            command_wrappers=[],
            command_attachments=[],
            shared_libs=[tilt],
            pre_run_hooks=[],
            post_run_hooks=[],
        )
        self.counter = 40

    @property
    def bench_src_path(self):
        return "."

    @staticmethod
    def get_build_var_names():
        return ["a"]

    @staticmethod
    def get_run_var_names():
        return ["c"]

    @staticmethod
    def get_tilt_var_names():
        return ["b"]

    def prebuild_bench(
        self,
        **kwargs,
    ):
        print("[BENCH] PREBUILD", kwargs)

    def single_run(
        self,
        **kwargs,
    ) -> str:
        method_args = {k: v for k, v in kwargs.items() if k not in ["platform"]}
        print("[BENCH] RUN", method_args)
        self.counter += 1
        return f"{self.counter}"

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        **_kwargs,
    ) -> RecordResult:
        counter = int(command_output)
        result_dict = {"out": counter}
        return result_dict

    def build_bench(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        **kwargs,
    ):
        assert benchmark_duration_seconds or not benchmark_duration_seconds
        print("[BENCH] BUILD", kwargs)

    def clean_bench(self):
        print("[BENCH] CLEAN")

    def build_tilt(self, **kwargs):
        print("[BENCH] BUILD TILT", kwargs)
        self.tilt.build_single_lock(**kwargs)


class TestBenchmark(unittest.TestCase):
    """Test suite of benchmark class."""

    @patch("sys.stdout", new_callable=StringIO)
    def test_benchmark(self, mock_stdout):
        """Test benchmark."""
        tilt = TiltMock()
        bench = BenchmarkMock(tilt=tilt)
        _, csv_path = tempfile.mkstemp(prefix="bench-", suffix=".csv")

        variables = [
            {"a": 1, "b": 11, "c": 21, "d": 31},
            {"a": 2, "b": 12, "c": 21, "d": 32},
            {"a": 1, "b": 12, "c": 22, "d": 31},
            {"a": 2, "b": 13, "c": 23, "d": 33},
        ]

        bench.configure_variables(
            experiment_name="{EXPERIMENT NAME}",
            benchmark_name="{BENCHMARK NAME}",
            csv_output_path=csv_path,
            base_data_dir=None,
            benchmark_duration_seconds=0,
            nb_runs=2,
            constants=None,
            variables=variables,
            pretty_variables=None,
            debug=False,
            gdb=False,
        )
        bench.run(other_campaigns_seconds=0, barrier=None, continuing=False)

        def filter_output(s, good_line):
            return "\n".join(line.strip() for line in s.split("\n") if good_line(line.strip()))

        def filter_stdout(s):
            def good_line(s: str) -> bool:
                return s.startswith("[BENCH] ") or s.startswith("[TILT] ")

            return filter_output(s, good_line)

        obtained_stdout = filter_stdout(mock_stdout.getvalue())

        expected_stdout = filter_stdout(
            """
            [TILT] CONFIGURE
            [TILT] CLEAN
            [BENCH] BUILD TILT {'b': 11}
            [TILT] BUILD {'b': 11}
            [BENCH] BUILD TILT {'b': 12}
            [TILT] BUILD {'b': 12}
            [BENCH] BUILD TILT {'b': 13}
            [TILT] BUILD {'b': 13}
            [BENCH] PREBUILD {'benchmark_duration_seconds': 0}
            [BENCH] CLEAN
            [BENCH] BUILD {'a': 1}
            [BENCH] RUN {'benchmark_duration_seconds': 0, 'build_variables': {'a': 1}, \
'record_data_dir': None, 'c': 21}
            [BENCH] RUN {'benchmark_duration_seconds': 0, 'build_variables': {'a': 1}, \
'record_data_dir': None, 'c': 21}
            [BENCH] RUN {'benchmark_duration_seconds': 0, 'build_variables': {'a': 1}, \
'record_data_dir': None, 'c': 22}
            [BENCH] RUN {'benchmark_duration_seconds': 0, 'build_variables': {'a': 1}, \
'record_data_dir': None, 'c': 22}
            [BENCH] CLEAN
            [BENCH] BUILD {'a': 2}
            [BENCH] RUN {'benchmark_duration_seconds': 0, 'build_variables': {'a': 2}, \
'record_data_dir': None, 'c': 21}
            [BENCH] RUN {'benchmark_duration_seconds': 0, 'build_variables': {'a': 2}, \
'record_data_dir': None, 'c': 21}
            [BENCH] RUN {'benchmark_duration_seconds': 0, 'build_variables': {'a': 2}, \
'record_data_dir': None, 'c': 23}
            [BENCH] RUN {'benchmark_duration_seconds': 0, 'build_variables': {'a': 2}, \
'record_data_dir': None, 'c': 23}
        """
        )

        self.assertEqual(obtained_stdout, expected_stdout)

        def filter_csv(s):
            def good_line(s: str) -> bool:
                return s and not s.startswith("#")

            return filter_output(s, good_line)

        with open(csv_path, "r") as csv_file:
            obtained_csv = filter_csv(csv_file.read())

        expected_csv = filter_csv(
            """
            experiment_name;benchmark_name;a;c;b;d;rep;out
            {EXPERIMENT NAME};{BENCHMARK NAME};1;21;11;31;1;41
            {EXPERIMENT NAME};{BENCHMARK NAME};1;21;11;31;2;42
            {EXPERIMENT NAME};{BENCHMARK NAME};1;22;12;31;1;43
            {EXPERIMENT NAME};{BENCHMARK NAME};1;22;12;31;2;44
            {EXPERIMENT NAME};{BENCHMARK NAME};2;21;12;32;1;45
            {EXPERIMENT NAME};{BENCHMARK NAME};2;21;12;32;2;46
            {EXPERIMENT NAME};{BENCHMARK NAME};2;23;13;33;1;47
            {EXPERIMENT NAME};{BENCHMARK NAME};2;23;13;33;2;48
        """
        )

        self.assertEqual(obtained_csv, expected_csv)


if __name__ == "__main__":
    unittest.main()
