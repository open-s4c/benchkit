#!/usr/bin/env python3
# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT


from benchkit.communication.pty import PtyCommLayer
from typing import List

import pathlib
import re
import os
import select
import subprocess
import threading

def thread(port: pathlib.Path):
    decoded: str
    with PtyCommLayer(port=port) as pty:
        out: bytearray = pty.listen(timeout=5.0) # big timeout to take latencies into account
        if not len(out):
            print("nothing was received")
        decoded = out.decode(errors="replace")

    print(decoded)
    assert decoded == "hello\n"

if __name__ == "__main__":
    command: List[str] = ["socat", "-d", "-d", "pty,raw,echo=0", "pty,raw,echo=0"] # opens two linked PTYs
    fakepty = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stdin=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=False,
                               bufsize=0,)

    buf = b""
    if (stdout := fakepty.stderr) is not None:
        while True:
            r, _, _ = select.select([stdout], [], [], 1.0)
            if not r:
                break

            chunk = os.read(stdout.fileno(), 512)
            if not chunk:
                break

            buf += chunk

    decoded: str = buf.decode(errors="replace")
    pty = re.findall(r"/dev/pts/\d+", decoded)
    print(pty)

    listener = threading.Thread(target=thread, args=(pathlib.Path(pty[1]),))
    listener.start()
    with PtyCommLayer(port=pathlib.Path(pty[0])) as pty0:
        pty0.shell(command="hello", print_input=False)
    listener.join()
