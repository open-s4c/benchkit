# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Result stores for benchkit campaigns.

A `ResultStore` owns everything downstream of a produced record: how results
are laid out on disk, in which formats, and how previously stored results are
read back for resuming. Benchmarks produce records; stores persist them.

One class per format, plus a composite:

- `CsvStore` writes the campaign CSV, appended record by record (live
  journal), with a role-namespaced header: `identity/experiment_name;
  constant/hostname;input/nb_threads;rep;output/throughput;
  pretty/nb_threads_pretty;...`. The header is the union schema of the
  records seen so far, rendered in deterministic section order (identity,
  constants, inputs, rep, outputs, pretty); when a record introduces a new
  column, the file is rewritten atomically with the extended header. Rows
  are always rendered against the current header, so columns can never
  silently misalign. The CSV is also the resume journal (`existing_records`).
- `JsonStore` writes one `metadata.json` per campaign (in the campaign data
  directory) holding the provenance previously stored as `#` comment lines
  in the CSV (dates, git revision, kernel, durations, ...), plus one
  role-structured `experiment_results.json` per record directory.
- `CsvJsonStore` composes the two behind the `ResultStore` protocol; it is
  the default store of legacy campaigns.

The CSV is a convenience denormalization of the record hierarchy, not the
source of truth. Roles make record identity explicit: a resume/caching
implementation can match on `identity/* + constant/* + input/* + rep`
without guessing which columns are outputs.

Later slices consolidate store selection onto the engine
(`ExecutionEngine(store=..., generator=..., policy=...)`).
"""

import json
import os
import pathlib
from collections.abc import Sequence
from typing import Any, Dict, List, Optional, Protocol

from benchkit.utils.misc import CSV_SEPARATOR
from benchkit.utils.types import PathType, Pretty

Record = Dict[str, Any]

ROLE_IDENTITY = "identity"
ROLE_CONSTANT = "constant"
ROLE_INPUT = "input"
ROLE_OUTPUT = "output"
ROLE_PRETTY = "pretty"
REP_COLUMN = "rep"

_ROLE_ORDER = (ROLE_IDENTITY, ROLE_CONSTANT, ROLE_INPUT, ROLE_OUTPUT, ROLE_PRETTY)
_ROLE_PREFIXES = tuple(f"{role}/" for role in _ROLE_ORDER)

_METADATA_FILENAME = "metadata.json"
_METADATA_VERSION = 1
_RECORD_JSON_FILENAME = "experiment_results.json"


def strip_role(column: str) -> str:
    """
    Return the bare name of a role-namespaced CSV column.

    Args:
        column (str):
            a CSV column name, possibly prefixed with a role (e.g. "input/nb_threads").

    Returns:
        str: the column name without its role prefix ("nb_threads"); a column
        without a known role prefix is returned unchanged.
    """
    for prefix in _ROLE_PREFIXES:
        if column.startswith(prefix):
            return column[len(prefix) :]
    return column


def _compute_pretty(
    pretty_variables: Pretty | None,
    base: Record,
) -> Record:
    # Ported from the legacy Benchmark._update_pretty_variables, values
    # rendered identically (including the historical quoting).
    pretty: Record = {}
    if not pretty_variables:
        return pretty
    for var_name, ugly2pretty in pretty_variables.items():
        ugly_var_value = base.get(var_name)

        if not isinstance(ugly2pretty, dict):
            # If the pretty variable is not a dict, assume it is the pretty column name
            pretty[ugly2pretty] = ugly_var_value
            continue

        if isinstance(ugly_var_value, Sequence) and not isinstance(ugly_var_value, str):
            ugly_var_value = ugly_var_value[0]

        pretty_var_value = ugly2pretty.get(ugly_var_value, ugly_var_value)
        pretty[f"{var_name}_pretty"] = f'"{pretty_var_value}"'
        # If __category__ is defined, also create a column with that name
        category = ugly2pretty.get("__category__")
        if category is not None:
            pretty[category] = f'"{pretty_var_value}"'
    return pretty


class ResultStore(Protocol):
    """
    Protocol describing a store of campaign results.

    Structural typing: any object with the conforming methods is a valid
    store; no inheritance is required. The store must not assume a finite
    upfront number of records (generators may be unbounded or adaptive).
    """

    def existing_records(self) -> List[Record]:
        """
        Return the records already persisted by a previous, interrupted campaign run.

        Returns:
            List[Record]: previously stored records with bare (un-namespaced)
            column names; empty if nothing was persisted before.
        """
        ...

    def begin(self, metadata: Record) -> None:
        """
        Open the store for a campaign run and persist its metadata.

        Args:
            metadata (Record):
                campaign-level provenance (name, dates, git revision, kernel, ...).
        """
        ...

    def write_record(
        self,
        identity: Record,
        constants: Record,
        inputs: Record,
        rep: int,
        outputs: Record,
        record_data_dir: Optional[PathType],
    ) -> None:
        """
        Persist one produced record.

        Args:
            identity (Record):
                columns identifying the campaign (experiment name, benchmark name).
            constants (Record):
                constant columns of the campaign.
            inputs (Record):
                the record's input parameters (variables).
            rep (int):
                repetition index of this run (1-based).
            outputs (Record):
                the output variables produced by the run (one record).
            record_data_dir (Optional[PathType]):
                the record's data directory, where per-record files are stored.
        """
        ...

    def end(self, metadata: Record) -> None:
        """
        Close the store for this campaign run and complete its metadata.

        Args:
            metadata (Record):
                metadata to merge into the campaign metadata (actual duration, ...).
        """
        ...


class CsvStore:
    """
    Store campaign results as a single role-namespaced CSV file.

    The CSV doubles as the resume journal: when `continuing` is set, the
    pre-existing file is loaded and its records are exposed through
    `existing_records()`. A header loaded from a pre-existing file keeps its
    on-file column order (possibly a legacy layout); new columns are then
    appended at the end instead of re-grouped into sections.
    """

    def __init__(
        self,
        csv_output_path: PathType,
        pretty_variables: Pretty | None = None,
        continuing: bool = False,
    ) -> None:
        """
        Args:
            csv_output_path (PathType):
                path of the campaign CSV file.
            pretty_variables (Pretty | None, optional):
                pretty translation of variable values; generates `pretty/` columns.
            continuing (bool, optional):
                whether the store appends to the results of an interrupted run.
        """
        self._csv_path = pathlib.Path(csv_output_path)
        self._pretty_variables = pretty_variables

        # Column names (with role prefix) per section, in first-seen order:
        self._sections: Dict[str, List[str]] = {role: [] for role in _ROLE_ORDER}
        self._header: List[str] = []
        # All rows written so far, keyed by prefixed column name, buffered to
        # allow an atomic full rewrite when the schema grows:
        self._rows: List[Dict[str, str]] = []
        self._header_from_file = False

        if continuing:
            self._load_existing_csv()

    @property
    def csv_path(self) -> pathlib.Path:
        """
        Return the path of the campaign CSV file.

        Returns:
            pathlib.Path: the path of the campaign CSV file.
        """
        return self._csv_path

    def existing_records(self) -> List[Record]:
        """
        Return the records read back from a pre-existing campaign CSV.

        Returns:
            List[Record]: previously stored records with bare column names;
            empty when not continuing or when no previous CSV exists.
        """
        return [{strip_role(k): v for k, v in row.items()} for row in self._rows]

    def begin(self, metadata: Record) -> None:
        """
        Open the store for a campaign run. Campaign metadata is not stored
        in the CSV; see `JsonStore`.

        Args:
            metadata (Record): ignored by this store.
        """

    def write_record(
        self,
        identity: Record,
        constants: Record,
        inputs: Record,
        rep: int,
        outputs: Record,
        record_data_dir: Optional[PathType] = None,
    ) -> None:
        """
        Append one produced record to the CSV: one record, one row.

        Args:
            identity (Record):
                columns identifying the campaign (experiment name, benchmark name).
            constants (Record):
                constant columns of the campaign.
            inputs (Record):
                the record's input parameters (variables).
            rep (int):
                repetition index of this run (1-based).
            outputs (Record):
                the output variables produced by the run (one record).
            record_data_dir (Optional[PathType], optional):
                ignored by this store.
        """
        pretty = _compute_pretty(
            pretty_variables=self._pretty_variables,
            base=identity | constants | inputs,
        )

        row: Dict[str, str] = {}
        for role, values in (
            (ROLE_IDENTITY, identity),
            (ROLE_CONSTANT, constants),
            (ROLE_INPUT, inputs),
        ):
            for name, value in values.items():
                row[self._column(role=role, name=name)] = str(value)
        row[REP_COLUMN] = str(rep)
        for name, value in outputs.items():
            row[self._column(role=ROLE_OUTPUT, name=name)] = str(value)
        for name, value in pretty.items():
            row[self._column(role=ROLE_PRETTY, name=name)] = str(value)

        self._write_rows(rows=[row])

    def end(self, metadata: Record) -> None:
        """
        Close the store for this campaign run. Campaign metadata is not
        stored in the CSV; see `JsonStore`.

        Args:
            metadata (Record): ignored by this store.
        """

    def _column(self, role: str, name: str) -> str:
        column = f"{role}/{name}"
        if column not in self._sections[role]:
            self._sections[role].append(column)
        return column

    def _current_header(self) -> List[str]:
        header = list(self._sections[ROLE_IDENTITY])
        header += self._sections[ROLE_CONSTANT]
        header += self._sections[ROLE_INPUT]
        header.append(REP_COLUMN)
        header += self._sections[ROLE_OUTPUT]
        header += self._sections[ROLE_PRETTY]
        return header

    def _write_rows(self, rows: List[Dict[str, str]]) -> None:
        for row in rows:
            self._register_columns(row)

        if not self._header:
            self._header = self._current_header()
            with open(self._csv_path, "a") as csv_file:
                self._write_line(content=CSV_SEPARATOR.join(self._header), file=csv_file)
        else:
            new_columns = [c for c in self._current_header() if c not in self._header]
            if new_columns:
                if self._header_from_file:
                    self._header = self._header + new_columns
                else:
                    self._header = self._current_header()
                self._rewrite_csv()

        with open(self._csv_path, "a") as csv_file:
            for row in rows:
                line = CSV_SEPARATOR.join(row.get(column, "") for column in self._header)
                self._write_line(content=line, file=csv_file)
                self._rows.append(row)

    def _register_columns(self, row: Dict[str, str]) -> None:
        for column in row:
            if column == REP_COLUMN:
                continue
            for role in _ROLE_ORDER:
                if column.startswith(f"{role}/"):
                    if column not in self._sections[role]:
                        self._sections[role].append(column)
                    break
            else:
                # Bare column from a legacy (pre-namespacing) CSV: keep it in
                # the output section so appends stay possible.
                if column not in self._sections[ROLE_OUTPUT]:
                    self._sections[ROLE_OUTPUT].append(column)

    def _rewrite_csv(self) -> None:
        # Atomic rewrite: the whole file is regenerated with the extended
        # header, then swapped in place. An observer tailing the file loses
        # the inode; a crash leaves the previous complete file untouched.
        tmp_path = self._csv_path.with_suffix(".csv.tmp")
        with open(tmp_path, "w") as csv_file:
            print(CSV_SEPARATOR.join(self._header), file=csv_file)
            for row in self._rows:
                print(
                    CSV_SEPARATOR.join(row.get(column, "") for column in self._header),
                    file=csv_file,
                )
        os.replace(tmp_path, self._csv_path)

    def _load_existing_csv(self) -> None:
        if not self._csv_path.exists():
            return
        with open(self._csv_path, "r") as csv_file:
            lines = [
                line.strip()
                for line in csv_file.readlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        if not lines:
            return
        header = lines[0].split(CSV_SEPARATOR)
        rows = [dict(zip(header, line.split(CSV_SEPARATOR))) for line in lines[1:]]
        for row in rows:
            self._register_columns(row)
        # Preserve the on-file header order (it may be a legacy layout):
        self._header = header
        self._header_from_file = True
        self._rows = rows

    @staticmethod
    def _write_line(content: str, file: Any) -> None:
        # Flushed line by line so the journal stays tail-able and survives crashes.
        print(content, file=file)
        file.flush()


class JsonStore:
    """
    Store campaign metadata and per-record results as JSON files.

    `metadata.json` lives in the campaign data directory and holds the
    campaign-level provenance; it is written at `begin()` and completed at
    `end()`. Each record directory receives a role-structured
    `experiment_results.json`.
    """

    def __init__(
        self,
        base_data_dir: Optional[PathType],
        pretty_variables: Pretty | None = None,
        continuing: bool = False,
        json_encoder: Optional[type] = None,
    ) -> None:
        """
        Args:
            base_data_dir (Optional[PathType]):
                campaign data directory where `metadata.json` is stored;
                campaign metadata is skipped if None.
            pretty_variables (Pretty | None, optional):
                pretty translation of variable values; stored in the record JSON.
            continuing (bool, optional):
                whether to merge into the metadata of an interrupted run.
            json_encoder (Optional[type], optional):
                JSONEncoder subclass used to serialize record values.
        """
        self._base_data_dir = pathlib.Path(base_data_dir) if base_data_dir is not None else None
        self._pretty_variables = pretty_variables
        self._json_encoder = json_encoder
        self._metadata: Record = {"metadata_version": _METADATA_VERSION}

        if continuing:
            self._load_existing_metadata()

    @property
    def metadata_path(self) -> Optional[pathlib.Path]:
        """
        Return the path of the campaign metadata file.

        Returns:
            Optional[pathlib.Path]: the path of `metadata.json`, or None if the
            store has no data directory.
        """
        if self._base_data_dir is None:
            return None
        return self._base_data_dir / _METADATA_FILENAME

    def existing_records(self) -> List[Record]:
        """
        Return the records already persisted by a previous campaign run.

        Returns:
            List[Record]: always empty; resuming from the record hierarchy is
            a planned evolution; the CSV journal is the resume source today.
        """
        return []

    def begin(self, metadata: Record) -> None:
        """
        Open the store for a campaign run and persist its metadata.

        Args:
            metadata (Record):
                campaign-level provenance (name, dates, git revision, kernel, ...).
        """
        self._metadata.update(metadata)
        self._write_metadata()

    def write_record(
        self,
        identity: Record,
        constants: Record,
        inputs: Record,
        rep: int,
        outputs: Record,
        record_data_dir: Optional[PathType] = None,
    ) -> None:
        """
        Write the role-structured record JSON into the record data directory.

        Args:
            identity (Record):
                columns identifying the campaign (experiment name, benchmark name).
            constants (Record):
                constant columns of the campaign.
            inputs (Record):
                the record's input parameters (variables).
            rep (int):
                repetition index of this run (1-based).
            outputs (Record):
                the output variables produced by the run (one record).
            record_data_dir (Optional[PathType], optional):
                the record's data directory; the JSON is skipped if None.
        """
        if record_data_dir is None:
            return
        record = {
            "identity": identity,
            "constants": constants,
            "inputs": inputs,
            "rep": rep,
            "outputs": outputs,
            "pretty": _compute_pretty(
                pretty_variables=self._pretty_variables,
                base=identity | constants | inputs,
            ),
        }
        json_path = pathlib.Path(record_data_dir) / _RECORD_JSON_FILENAME
        content = json.dumps(record, indent=4, cls=self._json_encoder).strip() + "\n"
        json_path.write_text(content)

    def end(self, metadata: Record) -> None:
        """
        Close the store for this campaign run and complete its metadata.

        Args:
            metadata (Record):
                metadata to merge into the campaign metadata (actual duration, ...).
        """
        self._metadata.update(metadata)
        self._write_metadata()

    def _write_metadata(self) -> None:
        metadata_path = self.metadata_path
        if metadata_path is None:
            return
        content = json.dumps(self._metadata, indent=4, cls=self._json_encoder).strip() + "\n"
        metadata_path.write_text(content)

    def _load_existing_metadata(self) -> None:
        metadata_path = self.metadata_path
        if metadata_path is None or not metadata_path.exists():
            return
        self._metadata.update(json.loads(metadata_path.read_text()))


class CsvJsonStore:
    """
    Compose a CsvStore and a JsonStore behind the ResultStore protocol.

    This is the default store of legacy campaigns: the CSV journal for live
    progress and resuming, the JSON files for structured provenance and
    per-record results.
    """

    def __init__(
        self,
        csv_output_path: PathType,
        base_data_dir: Optional[PathType],
        pretty_variables: Pretty | None = None,
        continuing: bool = False,
        json_encoder: Optional[type] = None,
    ) -> None:
        """
        Args:
            csv_output_path (PathType):
                path of the campaign CSV file.
            base_data_dir (Optional[PathType]):
                campaign data directory where `metadata.json` is stored.
            pretty_variables (Pretty | None, optional):
                pretty translation of variable values.
            continuing (bool, optional):
                whether the store appends to the results of an interrupted run.
            json_encoder (Optional[type], optional):
                JSONEncoder subclass used to serialize record values.
        """
        self._csv = CsvStore(
            csv_output_path=csv_output_path,
            pretty_variables=pretty_variables,
            continuing=continuing,
        )
        self._json = JsonStore(
            base_data_dir=base_data_dir,
            pretty_variables=pretty_variables,
            continuing=continuing,
            json_encoder=json_encoder,
        )
        self._stores = (self._csv, self._json)

    @property
    def csv_path(self) -> pathlib.Path:
        """
        Return the path of the campaign CSV file.

        Returns:
            pathlib.Path: the path of the campaign CSV file.
        """
        return self._csv.csv_path

    @property
    def metadata_path(self) -> Optional[pathlib.Path]:
        """
        Return the path of the campaign metadata file.

        Returns:
            Optional[pathlib.Path]: the path of `metadata.json`, or None if the
            store has no data directory.
        """
        return self._json.metadata_path

    def existing_records(self) -> List[Record]:
        """
        Return the records already persisted by a previous, interrupted campaign run.

        Returns:
            List[Record]: previously stored records with bare column names,
            read back from the CSV journal.
        """
        return self._csv.existing_records()

    def begin(self, metadata: Record) -> None:
        """
        Open the composed stores for a campaign run.

        Args:
            metadata (Record):
                campaign-level provenance (name, dates, git revision, kernel, ...).
        """
        for store in self._stores:
            store.begin(metadata=metadata)

    def write_record(
        self,
        identity: Record,
        constants: Record,
        inputs: Record,
        rep: int,
        outputs: Record,
        record_data_dir: Optional[PathType] = None,
    ) -> None:
        """
        Persist one produced record in all composed stores.

        Args:
            identity (Record):
                columns identifying the campaign (experiment name, benchmark name).
            constants (Record):
                constant columns of the campaign.
            inputs (Record):
                the record's input parameters (variables).
            rep (int):
                repetition index of this run (1-based).
            outputs (Record):
                the output variables produced by the run (one record).
            record_data_dir (Optional[PathType], optional):
                the record's data directory, where per-record files are stored.
        """
        for store in self._stores:
            store.write_record(
                identity=identity,
                constants=constants,
                inputs=inputs,
                rep=rep,
                outputs=outputs,
                record_data_dir=record_data_dir,
            )

    def end(self, metadata: Record) -> None:
        """
        Close the composed stores for this campaign run.

        Args:
            metadata (Record):
                metadata to merge into the campaign metadata (actual duration, ...).
        """
        for store in self._stores:
            store.end(metadata=metadata)
