# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from benchkit.core.bktypes.contexts import FetchContext
from benchkit.utils.fetchtools import fuseiso_mount, fuseiso_umount
from benchkit.utils.logging import configure_logging


def main() -> None:
    configure_logging(
        rich=True,
        level=logging.DEBUG,
        stdout_level=logging.INFO,
        file_level=logging.DEBUG,
    )

    benchkit_home_dir = Path("~/.benchkit/").expanduser().resolve()
    deps_dir = benchkit_home_dir / "deps"
    mnt_dir = benchkit_home_dir / "test-mnt"

    ctx = FetchContext(fetch_args={})
    comm = ctx.platform.comm

    if not comm.isdir(mnt_dir):
        comm.makedirs(path=mnt_dir, exist_ok=True)

    iso = deps_dir / "PATH_TO_ISO"

    fuseiso_mount(ctx=ctx, image=iso, mount_point=mnt_dir)
    fuseiso_umount(ctx=ctx, mount_point=mnt_dir)


if __name__ == "__main__":
    main()
