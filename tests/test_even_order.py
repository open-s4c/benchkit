# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to test the even order distribution, where each thread is scheduled on CPUs as far as
possible in the deep NUMA memory hierarchy.
"""

# flake8: noqa: E241

import unittest

from benchkit.platforms.evenorder import get_order


class TestEvenOrder(unittest.TestCase):
    """
    Test the even order distribution (where each thread is scheduled on CPUs as far as possible in
    the hierarchy).
    """

    def test_amdepyc2p24c(self):
        """Test AMD EPYC with 2x 24 cores."""
        # fmt: off
        expected_order = [
            95, 71, 92, 68, 89, 65, 86, 62,
            83, 59, 80, 56, 77, 53, 74, 50,
            94, 70, 91, 67, 88, 64, 85, 61,
            82, 58, 79, 55, 76, 52, 73, 49,
            93, 69, 90, 66, 87, 63, 84, 60,
            81, 57, 78, 54, 75, 51, 72, 48,
            47, 23, 44, 20, 41, 17, 38, 14,
            35, 11, 32,  8, 29,  5, 26,  2,
            46, 22, 43, 19, 40, 16, 37, 13,
            34, 10, 31,  7, 28,  4, 25,  1,
            45, 21, 42, 18, 39, 15, 36, 12,
            33,  9, 30,  6, 27,  3, 24,  0,
        ]
        # fmt: on
        nb_cpus = 96
        actual_order = get_order(
            nb_cpus=nb_cpus,
            nb_cache_partitions=16,
            nb_numa_nodes=2,
            nb_packages=2,
            nb_hyperthreads_per_core=2,
        )
        self.assertEqual(len(actual_order), nb_cpus)
        self.assertEqual(sorted(actual_order), list(range(nb_cpus)))
        self.assertEqual(expected_order, actual_order)

    def test_kunpeng9202p64c(self):
        """Test Kunpeng 920 with 2x 64 cores."""
        # fmt: off
        expected_order = [
            127,  63,  95,  31, 123,  59,  91,  27,
            119,  55,  87,  23, 115,  51,  83,  19,
            111,  47,  79,  15, 107,  43,  75,  11,
            103,  39,  71,   7,  99,  35,  67,   3,
            126,  62,  94,  30, 122,  58,  90,  26,
            118,  54,  86,  22, 114,  50,  82,  18,
            110,  46,  78,  14, 106,  42,  74,  10,
            102,  38,  70,   6,  98,  34,  66,   2,
            125,  61,  93,  29, 121,  57,  89,  25,
            117,  53,  85,  21, 113,  49,  81,  17,
            109,  45,  77,  13, 105,  41,  73,   9,
            101,  37,  69,   5,  97,  33,  65,   1,
            124,  60,  92,  28, 120,  56,  88,  24,
            116,  52,  84,  20, 112,  48,  80,  16,
            108,  44,  76,  12, 104,  40,  72,   8,
            100,  36,  68,   4,  96,  32,  64,   0,
        ]
        # fmt: on
        nb_cpus = 128
        actual_order = get_order(
            nb_cpus=nb_cpus,
            nb_cache_partitions=32,
            nb_numa_nodes=4,
            nb_packages=2,
            nb_hyperthreads_per_core=1,
        )
        self.assertEqual(len(actual_order), nb_cpus)
        self.assertEqual(sorted(actual_order), list(range(nb_cpus)))
        self.assertEqual(expected_order, actual_order)

    def test_kunpeng9202p48c(self) -> None:
        """Test Kunpeng 920 with 2x 48 cores."""
        # fmt: off
        expected_order = [
            95, 47, 71, 23, 91, 43, 67, 19, 87, 39, 63, 15,
            83, 35, 59, 11, 79, 31, 55,  7, 75, 27, 51,  3,
            94, 46, 70, 22, 90, 42, 66, 18, 86, 38, 62, 14,
            82, 34, 58, 10, 78, 30, 54,  6, 74, 26, 50,  2,
            93, 45, 69, 21, 89, 41, 65, 17, 85, 37, 61, 13,
            81, 33, 57,  9, 77, 29, 53,  5, 73, 25, 49,  1,
            92, 44, 68, 20, 88, 40, 64, 16, 84, 36, 60, 12,
            80, 32, 56,  8, 76, 28, 52,  4, 72, 24, 48,  0,
        ]
        # fmt: on
        nb_cpus = 96
        actual_order = get_order(
            nb_cpus=nb_cpus,
            nb_cache_partitions=24,
            nb_numa_nodes=4,
            nb_packages=2,
            nb_hyperthreads_per_core=1,
        )
        self.assertEqual(len(actual_order), nb_cpus)
        self.assertEqual(sorted(actual_order), list(range(nb_cpus)))
        self.assertEqual(expected_order, actual_order)


if __name__ == "__main__":
    unittest.main()
