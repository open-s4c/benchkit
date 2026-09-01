# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Record generators for benchkit campaigns.

A `RecordGenerator` describes *what is explored* by a campaign: it produces
the records (variable-name to value mappings) that the execution engine
turns into benchmark runs. Exploration strategies become pluggable values
instead of being hardwired into the campaign classes.

This module provides the two finite generators:

- `CartesianGenerator`: the cartesian product of a variable space, the
  current default exploration strategy;
- `ListGenerator`: a pre-built list of records, iterated in order;
- `FilteredGenerator`: a combinator wrapping any generator to yield only
  the records passing a predicate.

Feedback-driven generators (adaptive search, pruning, calibration loops)
plug into the same protocol in a later phase, once the engine drives
generation lazily; today the campaign materializes the records once at
construction time.
"""

from typing import Any, Callable, Dict, Iterable, Iterator, Protocol

from benchkit.utils.variables import cartesian_product

Record = Dict[str, Any]


class RecordGenerator(Protocol):
    """
    Protocol describing a generator of campaign records.

    Structural typing: any object with a conforming `records()` method is a
    valid generator; no inheritance is required.
    """

    def records(self) -> Iterator[Record]:
        """
        Return a fresh iteration over the records of the parameter space.

        Contract: every call starts a new iteration from the beginning;
        implementations must be re-iterable, not one-shot iterators.

        Returns:
            Iterator[Record]: the records, one variable-name to value
            mapping per benchmark configuration.
        """
        ...


class CartesianGenerator:
    """
    Generate the cartesian product of a variable space.

    Every combination of the given variable values yields one record, in
    the same order as the historical cartesian campaigns.
    """

    def __init__(
        self,
        variables: Dict[str, Iterable[Any]],
    ) -> None:
        """
        Args:
            variables (Dict[str, Iterable[Any]]):
                mapping from variable name to the values it takes.
                Values are materialized at construction so that the
                generator stays re-iterable.
        """
        self._variables = {
            name: (values if isinstance(values, dict) else list(values))
            for name, values in variables.items()
        }

    def records(self) -> Iterator[Record]:
        """
        Return a fresh iteration over the cartesian product of the variables.

        Returns:
            Iterator[Record]: one record per combination of variable values.
        """
        return cartesian_product(self._variables)


class ListGenerator:
    """
    Generate records from a pre-built list, in order.

    This is the exploration strategy behind "iterate variables" campaigns,
    where the caller provides the records explicitly.
    """

    def __init__(
        self,
        records: Iterable[Record],
    ) -> None:
        """
        Args:
            records (Iterable[Record]):
                the records to generate; materialized at construction so
                that the generator stays re-iterable.
        """
        self._records = list(records)

    def records(self) -> Iterator[Record]:
        """
        Return a fresh iteration over the provided records.

        Returns:
            Iterator[Record]: the records, in the provided order.
        """
        return iter(self._records)


class FilteredGenerator:
    """
    Wrap another generator to yield only the records passing a predicate.

    Composes with any RecordGenerator, preserving the order of the wrapped
    generator's records.
    """

    def __init__(
        self,
        generator: RecordGenerator,
        predicate: Callable[[Record], bool],
    ) -> None:
        """
        Args:
            generator (RecordGenerator):
                the generator whose records are filtered.
            predicate (Callable[[Record], bool]):
                keep a record iff this callable returns True for it.
        """
        self._generator = generator
        self._predicate = predicate

    def records(self) -> Iterator[Record]:
        """
        Return a fresh iteration over the wrapped records passing the predicate.

        Returns:
            Iterator[Record]: the kept records, in the wrapped generator's order.
        """
        return filter(self._predicate, self._generator.records())
