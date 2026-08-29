# APUE I/O Efficiency Benchmark (Figure 3.6)

Reproduces the classic APUE (Advanced Programming in the Unix Environment)
Figure 3.6 experiment: measuring I/O efficiency as a function of `BUFFSIZE`
when copying a file with `read()`/`write()`.

## How to run

```bash
cd examples/apue_io
python3 campaign_apue_io.py
```

Results (CSV) are written to `~/.benchkit/results/`.

## What it does

1. **Generates** a deterministic 516,581,760-byte (~493 MiB) input file.
2. **Compiles** `src/apue_copy.c` with `-DBUFFSIZE=N` for each N in
   {16, 32, 64, ..., 524288} (16 powers of two). The 1-8 values from the
   original APUE table are skipped because they cause 500M+ syscalls per
   run and are very slow.
3. **Runs** each binary 5 times, redirecting stdin from the dataset and
   stdout to `/dev/null`, timed by `/usr/bin/time`.
4. **Collects** user CPU, system CPU, wall-clock time, loop count, and
   derived throughput (MiB/s).

## Cache control

Before each run the input file is evicted from the page cache using
`posix_fadvise(POSIX_FADV_DONTNEED)`. This works without root privileges.

## Prerequisites

- Linux with `gcc` and `/usr/bin/time` (GNU time) installed.
- Python 3.10+ with benchkit installed.
