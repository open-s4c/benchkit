# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Multi-index-group-by data structure to convert list of records with common (build or run) variables
into a hierarchical structure.
"""

import itertools
from typing import Any, Dict, Iterable, Iterator, List, Tuple

MultiIndexGroupby = Dict[str, Any] | List[Dict[str, Any]]
ListGroupby = List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]


def cartesian_product(variables: Dict[str, Iterable[Any]]) -> Iterator[Dict[str, Any]]:
    """
    Return the cartesian products of the given variables.

    Args:
        variables (Dict[str, Iterable[Any]]): set of variables to multiply to each other.

    Returns:
        Iterator[Dict[str, Any]]: cartesian product if the given variables.

    Yields:
        Iterator[Dict[str, Any]]: cartesian product if the given variables.
    """
    non_empty_variables = {k: v for k, v in variables.items() if v}
    product_gen = (
        dict(zip(non_empty_variables.keys(), record))
        for record in itertools.product(*non_empty_variables.values())
    )
    return product_gen


def multi_index_groupby(
    variables_names: Iterable[str],
    bench_variables: Iterable[Dict[str, Any]],
) -> MultiIndexGroupby:
    """
    Returns a multi-index groupby dict, representing a tree where leaves are list of records with
    the same variable values from the root to the leaf. The chosen variables to group the records
    together are given as input.

    Args:
        variables_names (Iterable[str]): names of the variables.
        bench_variables (Iterable[Dict[str, Any]]): variables of the benchmark.

    Returns:
        MultiIndexGroupby: migb representing the variables hierarchically.
    """
    vn = list(variables_names)
    if not vn:
        return list(bench_variables)
    migb: MultiIndexGroupby = {}
    for record in bench_variables:
        current_dict = migb
        for key in vn[:-1]:
            current_key = None
            if key in record:
                current_key = record[key]
            if current_key not in current_dict:
                current_dict[current_key] = {}
            current_dict = current_dict[current_key]
        key = vn[-1]
        current_key = None
        if key in record:
            current_key = record[key]
        if current_key not in current_dict:
            current_dict[current_key] = []
        current_dict[current_key].append(record)
    return migb


def list_groupby_from_multi_index_groupby(
    multi_index_groupby_object: MultiIndexGroupby,
    variables_names: Iterable[str],
) -> ListGroupby:
    """
    Convert the migb into a list.

    Args:
        multi_index_groupby_object (MultiIndexGroupby): migb.
        variables_names (Iterable[str]): names of the variables to consider.

    Raises:
        ValueError: if the structure of the given migb is wrong.

    Returns:
        ListGroupby: the list created from the migb.

    Yields:
        Iterator[ListGroupby]: the list created from the migb.
    """
    index = {}
    vn = list(variables_names)

    def recurse(migb, pos):
        if isinstance(migb, dict):
            for key, value in migb.items():
                index[vn[pos]] = key
                yield from recurse(value, pos + 1)
        elif isinstance(migb, list):
            yield index.copy(), migb
        else:
            raise ValueError("unknown value in multi-index groupby dict")

    yield from recurse(multi_index_groupby_object, 0)


def list_groupby(
    variables_names: Iterable[str],
    bench_variables: Iterable[Dict[str, Any]],
) -> ListGroupby:
    """
    Return the list groupby from the benchmark variables.

    Args:
        variables_names (Iterable[str]): names of the variables.
        bench_variables (Iterable[Dict[str, Any]]): benchmark variables.

    Returns:
        ListGroupby: the list groupby from the benchmark variables.
    """
    vn = list(variables_names)
    migb = multi_index_groupby(vn, bench_variables)
    return list_groupby_from_multi_index_groupby(migb, vn)
