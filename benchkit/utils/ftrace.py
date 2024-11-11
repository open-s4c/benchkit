import time
from perfetto.trace_processor import TraceProcessor

from typing import Iterable, NamedTuple, Optional, Protocol, cast

from perfetto.trace_processor.api import QueryResultIterator

from benchkit.utils.types import Command, PathType

__default_span_query__ = """
    SELECT id, ts as timestamp, dur as duration, name
    FROM slice
"""
__default_track_query__ = """
    SELECT id AS track_id, name
    FROM counter_track
"""
__default_counter_query__ = """
    SELECT id, ts as timestamp, value, track_id
    FROM counter
"""


class SpanEvent(NamedTuple):
    id: int
    timestamp: int
    duration: float
    name: str


class TrackMapping(NamedTuple):
    track_id: int
    name: str


class RawCountEvent(NamedTuple):
    id: int
    timestamp: int
    value: int
    track_id: int


class CountEvent(NamedTuple):
    id: int
    timestamp: int
    name: str
    value: int


class FTrace:
    def __init__(
        self,
        path: str
    ) -> None:
        self.tp = TraceProcessor(trace=path)

    def query_raw(self, query: str) -> QueryResultIterator:
        result = self.tp.query(query)
        return result

    def query_spans(self) -> Iterable[SpanEvent]:
        events = self.query_raw(__default_span_query__)
        spans = [cast(SpanEvent, e) for e in events]
        return spans

    def query_counts(self) -> Iterable[CountEvent]:
        track_events = self.query_raw(__default_track_query__)
        tracks = [cast(TrackMapping, t) for t in track_events]
        mappings = {track.track_id: track.name for track in tracks}
        raw_events = self.query_raw(__default_counter_query__)
        raw_counts = [cast(RawCountEvent, e) for e in raw_events]

        events = []
        for rc in raw_counts:
            event = CountEvent(
                id=rc.id,
                timestamp=rc.timestamp,
                name=mappings.get(rc.track_id, "Unknown"),
                value=rc.value,
            )
            events.append(event)
        return events

