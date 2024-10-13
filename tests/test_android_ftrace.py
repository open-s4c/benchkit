#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Module to test reading ftrace from android devices
"""

import os, time

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


def collect_spans(file: str) -> List[Mapping]:
    events = []
    event_stack = []
    
    # TODO: fix this parsing, it seems to be incorrect
    with open(file, "r") as f:
        for line in f:
            if "tracing_mark_write" in line:
                line = line.strip()
                parts = line.split('tracing_mark_write:')
                timestamp: float
                if len(parts) == 2:
                    header, content = parts
                    # Extract timestamp
                    header_parts = header.strip().split()
                    if len(header_parts) >= 1:
                        timestamp_str = header_parts[-1].rstrip(':')
                        try:
                            timestamp = float(timestamp_str)
                        except ValueError:
                            # Skip lines with invalid timestamp
                            continue
                        content = content.strip()
                        if content.startswith('B|'):
                            # Begin event
                            parts = content.split('|', 2)
                            if len(parts) == 3:
                                _, pid, event_name = parts
                                event = {'name': event_name, 'start_time': timestamp, 'pid': pid}
                                event_stack.append(event)
                            else:
                                # Invalid format, skip
                                continue
                        elif content.startswith('E'):
                            # End event
                            if event_stack:
                                event = event_stack.pop()
                                event_name = event['name']
                                start_time = event['start_time']
                                pid = event.get('pid', '')
                                duration = timestamp - start_time
                                event['end_time'] = timestamp
                                event['duration'] = duration
                                events.append(event)
                            else:
                                # No matching begin event
                                continue
                        else:
                            # Instant event or other data
                            event = {'timestamp': timestamp, 'content': content}
                            events.append(event)
                    else:
                        # Invalid header format
                        continue

    return events


def main() -> None:
    device = AndroidDebugBridge._devices()[0]
    bridge = AndroidDebugBridge.from_device(device)

    enable_tracing(bridge)
    set_trace_buffer_size(bridge, TRACE_BUFFER_SIZE_KB)
    clear_trace_buffer(bridge)
    start_tracing(bridge)

    # demo code
    bridge.screen_tap(50, 50)
    open_website(bridge, EXAMPLE_WEBSITE)
    time.sleep(2)
    bridge.push_button_home()

    time.sleep(HOST_SLEEP_TIME)

    stop_tracing(bridge)
    disable_tracing(bridge)
    dump_trace(bridge, DEVICE_DUMP_PATH)

    bridge.pull(DEVICE_DUMP_PATH, HOST_DUMP_PATH)
    
    events = collect_spans(HOST_DUMP_PATH)
    for event in events:
        print(event)


if __name__ == "__main__":
    main()