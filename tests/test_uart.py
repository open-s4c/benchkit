#!/usr/bin/env python3
# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.communication.uart import UARTCommLayer
import pathlib

if __name__ == "__main__":
    """
    This test is meant to be run on a machine with a device connected to the
    /dev/ttyACM0 port, and that device should be sending data through UART. The
    test will listen for data on that port and print it out. Therefore, it is
    not a unit test, but rather shows the intended use of the UART.
    """
    uart = UARTCommLayer(port=pathlib.Path("/") / "dev" / "ttyACM0", ps1="")
    out = uart.listen(chunk_size=1, timeout=2.0)
