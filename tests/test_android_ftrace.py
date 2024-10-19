#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Module to test reading ftrace from android devices
"""

import time
from perfetto.trace_processor import TraceProcessor

from typing import List, Mapping
from benchkit.adb import AndroidDebugBridge


TRACE_BUFFER_SIZE_KB: int = 96000 
DEVICE_DUMP_PATH: str = "/sdcard/tmp/ftrace_dump"
HOST_DUMP_PATH: str = "./tests/tmp/ftrace_dump"
EXAMPLE_WEBSITE: str = "https://github.com/open-s4c/benchkit"
HOST_SLEEP_TIME: float = 5


def enable_tracing(bridge: AndroidDebugBridge) -> None:
    # per category tracing
    bridge.shell_out("echo 1 > /sys/kernel/tracing/events/irq/enable")
    # per event tracing
    bridge.shell_out("echo 1 > /sys/kernel/tracing/events/sched/sched_wakeup/enable")


def disable_tracing(bridge: AndroidDebugBridge) -> None:
    bridge.shell_out("echo 0 > /sys/kernel/tracing/events/irq/enable")
    bridge.shell_out("echo 0 > /sys/kernel/tracing/events/sched/sched_wakeup/enable")


def start_tracing(bridge: AndroidDebugBridge) -> None:
    bridge.shell_out("echo 1 > /sys/kernel/tracing/tracing_on")


def stop_tracing(bridge: AndroidDebugBridge) -> None:
    bridge.shell_out("echo 0 > /sys/kernel/tracing/tracing_on")


def dump_trace(bridge: AndroidDebugBridge, output: str) -> None:
    bridge.shell_out(f"rm {output} || true") # delete file or ignore rm if fails (file not exists)
    bridge.shell_out(f"cat /sys/kernel/tracing/trace > {output}")


def clear_trace_buffer(bridge: AndroidDebugBridge) -> None:
    bridge.shell_out("cat /dev/null > /sys/kernel/tracing/trace")


def set_trace_buffer_size(bridge: AndroidDebugBridge, size_kb: int) -> None:
    bridge.shell_out(f"echo {size_kb} > /sys/kernel/tracing/buffer_size_kb")


def open_website(bridge: AndroidDebugBridge, url: str) -> None:
    bridge.shell_out(f"am start -a android.intent.action.VIEW -d \"{url}\" com.android.chrome")


def print_ftrace_events(path: str) -> None:
    tp = TraceProcessor(trace=path)

    NS_TO_MS = 1e-6

    dutation_query = """
    SELECT ts, dur, name
    FROM slice
    """

    track_query = """
    SELECT id AS track_id, name
    FROM counter_track
    """

    counter_query = """
    SELECT ts, value, track_id
    FROM counter
    """

    print("Duration Events:")
    duration_events = tp.query(dutation_query)
    for row in duration_events:
        ts = row.ts
        name = row.name
        duration = row.dur * NS_TO_MS
        print(f"Duration Event ({ts}): {name}, Duration: {duration:.6f}ms")

    print()

    print("Counter Events:")
    track_events = tp.query(track_query)
    track_mapping = {row.track_id: row.name for row in track_events}

    counter_events = tp.query(counter_query)

    for row in counter_events:
        ts = row.ts
        track_id = row.track_id
        value = row.value
        counter_name = track_mapping.get(track_id, 'Unknown')

        print(f"Counter Event ({ts}): {counter_name}, Value: {value}")


def main() -> None:
    device = AndroidDebugBridge._devices()[0]
    bridge = AndroidDebugBridge.from_device(device)

    # enable and start tracing
    enable_tracing(bridge)
    set_trace_buffer_size(bridge, TRACE_BUFFER_SIZE_KB)
    clear_trace_buffer(bridge)
    start_tracing(bridge)

    # demo code to be traced (touch your device for more actions)
    bridge.screen_tap(50, 50)
    open_website(bridge, EXAMPLE_WEBSITE)
    time.sleep(2)
    bridge.push_button_home()
    time.sleep(HOST_SLEEP_TIME)

    # end tracing and pull data to pc
    stop_tracing(bridge)
    disable_tracing(bridge)
    dump_trace(bridge, DEVICE_DUMP_PATH)
    bridge.pull(DEVICE_DUMP_PATH, HOST_DUMP_PATH)

    print_ftrace_events(HOST_DUMP_PATH)


if __name__ == "__main__":
    main()
