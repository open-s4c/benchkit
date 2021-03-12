# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""Unit tests for variables and multi index group by."""

import unittest
from typing import Any, Iterable, List

from benchkit.utils.variables import cartesian_product, list_groupby
from benchkit.utils.variables import (
    list_groupby_from_multi_index_groupby as list_from_migb,
)
from benchkit.utils.variables import multi_index_groupby


class TestVariables(unittest.TestCase):
    """
    Unit tests for variables and multi index group by.
    """

    def assert_gen_equal(self, first: Iterable[Any], second: List[Any]):
        """Check two collections are equal."""
        self.assertEqual(list(first), second)

    def test_cartesian_product(self):
        """Test the cartesian product"""
        d = {"a": [1, 2, 3], "b": [4], "c": [5, 6]}
        cart = [
            {"a": 1, "b": 4, "c": 5},
            {"a": 1, "b": 4, "c": 6},
            {"a": 2, "b": 4, "c": 5},
            {"a": 2, "b": 4, "c": 6},
            {"a": 3, "b": 4, "c": 5},
            {"a": 3, "b": 4, "c": 6},
        ]
        self.assertEqual(list(cartesian_product(d)), cart)

        d = {"a": [2], "b": [3]}
        self.assertEqual(list(cartesian_product(d)), [{"a": 2, "b": 3}])

        d = {"a": [1, 2, 3], "b": [], "c": [5, 6]}
        cart = [
            {"a": 1, "c": 5},
            {"a": 1, "c": 6},
            {"a": 2, "c": 5},
            {"a": 2, "c": 6},
            {"a": 3, "c": 5},
            {"a": 3, "c": 6},
        ]
        self.assertEqual(list(cartesian_product(d)), cart)

    def test_multi_index_groupby(self):
        """Test multi index groupby data structure."""
        bench = [
            {"a": 1, "b": 4},
            {"a": 2, "b": 4},
            {"a": 2, "b": 3},
        ]

        migb_a = {1: [{"a": 1, "b": 4}], 2: [{"a": 2, "b": 4}, {"a": 2, "b": 3}]}
        migb_b = {4: [{"a": 1, "b": 4}, {"a": 2, "b": 4}], 3: [{"a": 2, "b": 3}]}
        migb_ab = {1: {4: [{"a": 1, "b": 4}]}, 2: {4: [{"a": 2, "b": 4}], 3: [{"a": 2, "b": 3}]}}
        migb_ba = {4: {1: [{"a": 1, "b": 4}], 2: [{"a": 2, "b": 4}]}, 3: {2: [{"a": 2, "b": 3}]}}

        self.assertEqual(multi_index_groupby(["a"], bench), migb_a)
        self.assertEqual(multi_index_groupby(["b"], bench), migb_b)
        self.assertEqual(multi_index_groupby(["a", "b"], bench), migb_ab)
        self.assertEqual(multi_index_groupby(["b", "a"], bench), migb_ba)

        self.assertEqual(multi_index_groupby([], bench), bench)

        l_a = [({"a": 1}, [{"a": 1, "b": 4}]), ({"a": 2}, [{"a": 2, "b": 4}, {"a": 2, "b": 3}])]
        l_ab = [
            ({"a": 1, "b": 4}, [{"a": 1, "b": 4}]),
            ({"a": 2, "b": 4}, [{"a": 2, "b": 4}]),
            ({"a": 2, "b": 3}, [{"a": 2, "b": 3}]),
        ]
        l_empty = [({}, bench)]

        self.assert_gen_equal(list_from_migb(migb_a, ["a"]), l_a)
        self.assert_gen_equal(list_from_migb(migb_ab, ["a", "b"]), l_ab)
        self.assert_gen_equal(list_from_migb(bench, []), l_empty)

        self.assert_gen_equal(list_groupby(["a"], bench), l_a)
        self.assert_gen_equal(list_groupby(["a", "b"], bench), l_ab)
        self.assert_gen_equal(list_groupby([], bench), l_empty)

    def test_multi_index_groupby_with_missing_keys(self):
        """Test migb when missing some keys."""
        bench = [
            {"a": 1, "c": 6},
            {"a": 1, "b": 4, "c": 5},
            {"a": 2, "b": 3},
            {"a": 2, "b": 4},
        ]

        migb_a = {
            1: [{"a": 1, "c": 6}, {"a": 1, "b": 4, "c": 5}],
            2: [{"a": 2, "b": 3}, {"a": 2, "b": 4}],
        }
        migb_b = {
            None: [{"a": 1, "c": 6}],
            4: [{"a": 1, "b": 4, "c": 5}, {"a": 2, "b": 4}],
            3: [{"a": 2, "b": 3}],
        }
        migb_ca = {
            6: {1: [{"a": 1, "c": 6}]},
            5: {1: [{"a": 1, "b": 4, "c": 5}]},
            None: {2: [{"a": 2, "b": 3}, {"a": 2, "b": 4}]},
        }

        self.assertEqual(multi_index_groupby(["a"], bench), migb_a)
        self.assertEqual(multi_index_groupby(["b"], bench), migb_b)
        self.assertEqual(multi_index_groupby(["c", "a"], bench), migb_ca)

        l_ca = [
            ({"a": 1, "c": 6}, [{"a": 1, "c": 6}]),
            ({"a": 1, "c": 5}, [{"a": 1, "b": 4, "c": 5}]),
            ({"a": 2, "c": None}, [{"a": 2, "b": 3}, {"a": 2, "b": 4}]),
        ]

        self.assert_gen_equal(list_from_migb(migb_ca, ["c", "a"]), l_ca)

        self.assert_gen_equal(list_groupby(["c", "a"], bench), l_ca)

    def test_multi_index_groupby_with_duplicates(self):
        """Test migb when there are duplicates."""
        bench = [{"a": 1, "b": 2}, {"a": 1, "b": 1}, {"a": 1, "b": 2}]

        migb_a = {1: bench}

        self.assertEqual(multi_index_groupby(["a"], bench), migb_a)

    def test_all(self):
        """Run all tests."""
        d = {"a": [1, 2, 3], "b": [4], "c": [5, 6]}
        cart = list(cartesian_product(d))

        self.assertEqual(multi_index_groupby(["b"], cart), {4: cart})

        def cart_c(val):
            dict_copy = d.copy()
            dict_copy["c"] = [val]
            return list(cartesian_product(dict_copy))

        self.assertEqual(multi_index_groupby(["c"], cart), {5: cart_c(5), 6: cart_c(6)})

        def abc(aval, bval, cval):
            return [{"a": aval, "b": bval, "c": cval}]

        migb_bca = {
            4: {
                5: {1: abc(1, 4, 5), 2: abc(2, 4, 5), 3: abc(3, 4, 5)},
                6: {1: abc(1, 4, 6), 2: abc(2, 4, 6), 3: abc(3, 4, 6)},
            }
        }
        self.assertEqual(multi_index_groupby(["b", "c", "a"], cart), migb_bca)


if __name__ == "__main__":
    unittest.main()
