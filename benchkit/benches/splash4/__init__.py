# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
"""
SPLASH-4 benchmark suite implementation for benchkit.

This module implements the benchkit protocol for SPLASH-4, a suite of parallel
scientific kernels/applications (FFT, LU, RADIX, OCEAN, BARNES, WATER, ...).
SPLASH-4 is built with the ``m4`` macro processor + ``make``: each benchmark's
``*.c.in`` source is expanded against the shared ``pthread.m4`` macro file into
``*.c`` and compiled. The default build uses ``-D ATOMIC_BARRIERS`` (SPLASH-4's
lock-free sense-reversing barriers).

Structure of this bench (mirrors ``benchkit/benches/npb``):
- fetch:   clone the SPLASH-4 repository
- build:   ``make`` the selected benchmark; the binary lands in its own dir. The
           selected kernel is a *build* variable; the resolved recipe is carried
           to ``run`` via ``BuildResult.other`` (the ``speccpu2017`` pattern).
- run:     execute the binary from *inside* the benchmark dir (inputs are
           resolved by relative path), with the thread count passed on the CLI
- collect: parse the ``TIMING INFORMATION`` block; the primary metric is
           ``Total time without initialization`` (the ROI / parallel region)
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from benchkit.core.bktypes import RecordResult
from benchkit.core.bktypes.callresults import BuildResult, FetchResult, RunResult
from benchkit.core.bktypes.contexts import BuildContext, CollectContext, FetchContext, RunContext
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.buildtools import make
from benchkit.utils.dir import get_benches_dir
from benchkit.utils.fetchtools import git_clone

SPLASH4_URL = "https://github.com/OdnetninI/Splash-4.git"
# Pinned to the currently-cloned HEAD ("Fix README"); update as needed.
SPLASH4_COMMIT = "Splash-4.0.1"


@dataclass(frozen=True)
class Splash4Kernel:
    """
    Static description of one SPLASH-4 benchmark.

    Attributes:
        subdir: directory under ``<repo>/Splash-4/`` holding the Makefile + *.c.in.
        binary: the TARGET produced by ``make`` (differs from the README's
            generic names, e.g. ``LU-NOCONT``, ``OCEAN-CONT``, ``WATER-NSQUARED``).
        args: CLI argument template; ``{n}`` = nb_threads, ``{size}`` = input size.
        size: default value substituted for ``{size}`` (None if unused).
        stdin: input-file template fed on stdin (``{n}``/``{size}``), or None.
    """

    subdir: str
    binary: str
    args: str = ""
    size: Optional[int] = None
    stdin: Optional[str] = None


# Inputs follow the README "Recommended Inputs"; adjust sizes per campaign
# (smaller inputs exist, e.g. barnes ships n8k in addition to n16384).
_BENCHES: dict[str, Splash4Kernel] = {
    # --- argument-based inputs ---
    "fft": Splash4Kernel(
        subdir="fft",
        binary="FFT",
        args="-p{n} -m{size}",
        size=16,
    ),
    "radix": Splash4Kernel(
        subdir="radix",
        binary="RADIX",
        args="-p{n} -n{size}",
        size=1048576,
    ),
    "lu": Splash4Kernel(
        subdir="lu-contiguous_blocks",
        binary="LU-CONT",
        args="-p{n} -n{size}",
        size=512,
    ),
    "lu-nc": Splash4Kernel(
        subdir="lu-non_contiguous_blocks",
        binary="LU-NOCONT",
        args="-p{n} -n{size}",
        size=512,
    ),
    "ocean": Splash4Kernel(
        subdir="ocean-contiguous_partitions",
        binary="OCEAN-CONT",
        args="-p{n} -n{size}",
        size=258,
    ),
    "ocean-nc": Splash4Kernel(
        subdir="ocean-non_contiguous_partitions",
        binary="OCEAN-NOCONT",
        args="-p{n} -n{size}",
        size=258,
    ),
    "radiosity": Splash4Kernel(
        subdir="radiosity",
        binary="RADIOSITY",
        args="-p {n} -ae 5000 -bf 0.1 -en 0.05 -room -batch",
    ),
    "raytrace": Splash4Kernel(
        subdir="raytrace",
        binary="RAYTRACE",
        args="-p{n} -m64 inputs/car.env",
    ),
    "volrend": Splash4Kernel(
        subdir="volrend",
        binary="VOLREND",
        args="{n} inputs/head 8",
    ),
    "volrend-npl": Splash4Kernel(
        subdir="volrend-no_print_lock",
        binary="VOLREND-NPL",
        args="{n} inputs/head 8",
    ),
    # --- stdin-based inputs (run via `bash -lc` for the `<` redirection) ---
    "cholesky": Splash4Kernel(
        subdir="cholesky",
        binary="CHOLESKY",
        args="-p{n}",
        stdin="inputs/tk15.O",
    ),
    "barnes": Splash4Kernel(
        subdir="barnes",
        binary="BARNES",
        size=16384,
        stdin="inputs/n{size}-p{n}",
    ),
    "fmm": Splash4Kernel(
        subdir="fmm",
        binary="FMM",
        size=16384,
        stdin="inputs/input.{n}.{size}",
    ),
    "water-nsq": Splash4Kernel(
        subdir="water-nsquared",
        binary="WATER-NSQUARED",
        size=512,
        stdin="inputs/n{size}-p{n}",
    ),
    "water-sp": Splash4Kernel(
        subdir="water-spatial",
        binary="WATER-SPATIAL",
        size=512,
        stdin="inputs/n{size}-p{n}",
    ),
}


class Splash4Bench:
    """
    Benchmark implementation for the SPLASH-4 suite.

    Only ``run`` is strictly required by the benchkit protocol; ``fetch``,
    ``build`` and ``collect`` are provided for a full fetch -> build -> run ->
    collect campaign.

    Variables:
        - ``benchmark`` is a *build* variable (it selects which binary is
          compiled). ``build`` resolves it and hands the recipe to ``run`` via
          ``BuildResult.other["kernel"]`` rather than requiring ``run`` to
          re-declare it.
        - ``nb_threads`` and ``input_size`` are *run* variables (SPLASH-4 takes
          them as CLI arguments at runtime; nothing is compiled in).
    """

    def fetch(
        self,
        ctx: FetchContext,
        parent_dir: Optional[Path] = None,
        commit: str = SPLASH4_COMMIT,
    ) -> FetchResult:
        """Clone the SPLASH-4 repository (idempotent via git_clone)."""
        parent_dir = get_benches_dir(parent_dir=parent_dir)
        repo_dir = git_clone(
            ctx=ctx,
            url=SPLASH4_URL,
            commit=commit,
            parent_dir=parent_dir,
        )
        return FetchResult(src_dir=repo_dir)

    def build(
        self,
        ctx: BuildContext,
        benchmark: str = "fft",
    ) -> BuildResult:
        """
        Build a single SPLASH-4 benchmark with ``make``.

        ``benchmark`` selects which kernel is compiled (a build-time choice). The
        binary is produced inside ``<repo>/Splash-4/<subdir>`` (also the run cwd,
        since inputs are resolved by relative path). The default build carries
        ``ATOMIC_BARRIERS`` from ``Makefile.config``.

        The resolved :class:`Splash4Kernel` is stored in ``BuildResult.other`` so
        that ``run`` does not need to re-take ``benchmark``.
        """
        kernel = self._kernel(benchmark)
        bench_dir = ctx.fetch_result.src_dir / "Splash-4" / kernel.subdir

        make(
            ctx,
            src_dir=bench_dir,
            targets=[kernel.binary],
            options={},
        )

        return BuildResult(build_dir=bench_dir, other={"kernel": kernel})

    def run(
        self,
        ctx: RunContext,
        nb_threads: int = 2,
        input_size: Optional[int] = None,
    ) -> RunResult:
        """
        Run the SPLASH-4 benchmark selected at build time, from its own directory.

        The kernel recipe is recovered from ``ctx.build_result.other["kernel"]``.
        Threads are passed on the command line (``-p<N>`` or a leading
        positional), not via an environment variable. Benchmarks reading their
        workload from stdin are run through ``bash -lc`` so the ``<`` redirection
        works (a first-class stdin parameter on the exec API would remove the
        shell wrapper).
        """
        kernel: Splash4Kernel = ctx.build_result.other["kernel"]
        bench_dir = ctx.build_result.build_dir
        size = input_size if input_size is not None else kernel.size

        command = f"./{kernel.binary}"
        if kernel.args:
            command += " " + kernel.args.format(n=nb_threads, size=size)
        if kernel.stdin:
            command += " < " + kernel.stdin.format(n=nb_threads, size=size)

        exec_out = ctx.exec(
            argv=["bash", "-lc", command],
            cwd=bench_dir,
            output_is_log=True,
        )
        return RunResult(outputs=[exec_out])

    def collect(self, ctx: CollectContext) -> RecordResult:
        """
        Parse the SPLASH-4 timing output into a record.

        SPLASH-4 kernels do not all print the same timing block:

        - Most (fft, lu*, ocean*, radix, cholesky, fmm, radiosity, raytrace)
          print ``Total time with/without initialization``. The "without
          initialization" value is the timed parallel region (the ROI), matching
          the ROI-only measurement used upstream. The label separator varies
          across kernels: ``:`` (fft/lu), tabs (radiosity) or spaces (raytrace).
        - barnes prints ``TRACKTIME`` (its main tracked compute time).
        - water-{nsquared,spatial} print ``Measured Time (2nd timestep onward)``.
        - volrend prints only per-frame times (no single total).

        Every record carries the **same** keys (uniform schema, so campaigns
        aggregate into a non-ragged CSV):

        - ``primary_time_us``: the kernel's headline timing in microseconds (the
          ROI where available; the bespoke time for barnes/water; None for
          volrend, which prints only per-frame times).
        - ``time_without_init_us`` / ``time_with_init_us``: the standard SPLASH-4
          ROI / whole-run times, or None for kernels that don't emit them.

        This never raises: an unparsed kernel yields all-None rather than failing
        the whole campaign point.
        """
        output = ctx.run_result.outputs[-1].stdout

        def _find(label: str) -> Optional[int]:
            # separator between label and value varies: ':' (fft/lu), tabs
            # (radiosity), spaces (raytrace), or '=' (barnes/water).
            m = re.search(rf"{label}[ \t:=]*(\d+)", output)
            return int(m.group(1)) if m else None

        # Standard timing block (fft, lu*, ocean*, radix, cholesky, fmm,
        # radiosity, raytrace).
        without_init = _find(r"Total time without initialization")
        with_init = _find(r"Total time with initialization")
        primary = without_init if without_init is not None else with_init

        # Bespoke timing output, detected by content, when the standard block is
        # absent: barnes -> TRACKTIME, water-* -> "Measured Time". (volrend has
        # no single total -> primary stays None.)
        if primary is None:
            primary = _find(r"TRACKTIME")
        if primary is None:
            primary = _find(r"Measured Time[^=]*")

        return {
            "primary_time_us": primary,
            "time_without_init_us": without_init,
            "time_with_init_us": with_init,
        }

    @staticmethod
    def _kernel(benchmark: str) -> Splash4Kernel:
        if benchmark not in _BENCHES:
            raise ValueError(
                f"Unknown SPLASH-4 benchmark '{benchmark}'. " f"Supported: {sorted(_BENCHES)}"
            )
        return _BENCHES[benchmark]

    @staticmethod
    def dependencies() -> list[PackageDependency]:
        """System packages required to build/run SPLASH-4 (Debian/Ubuntu names)."""
        return [
            PackageDependency("build-essential"),
            PackageDependency("m4"),
            PackageDependency("ivtools-dev"),
        ]

    @staticmethod
    def supported_benchmarks() -> list[str]:
        """Return the list of selectable SPLASH-4 benchmarks."""
        return sorted(_BENCHES)
