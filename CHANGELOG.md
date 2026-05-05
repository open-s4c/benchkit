# Changelog

All notable changes to benchkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.2] - 2026-05-05

This release accumulates 20 months of development since `0.0.1` (200+ merged PRs),
including the foundations of a redesigned API exposed as a forward-compatible
"new" engine alongside the legacy one. Highlights below.

### Added

- **New API and compat layer.** Introduced engines (`RunOnce` example),
  a `new -> old Campaign` adapter, a `compat` layer that propagates
  `other_variables`, applies wrappers/sharedlibs from new-style campaigns, and
  exposes a `pretty` option, paving the way for `0.1.0`.
- **New benchmarks (new API):** SPEC CPU 2017, NAS Parallel, Will-it-Scale,
  Kyoto Cabinet, Volano, LevelDB, Sleep, Heater (sequential & parallel).
- **New benchmarks (legacy API):** DaCapo benchmark suite (with Speedup
  Stacks), cyclictest, memcached, memtier, cloudsuite web-serving, Metis,
  GPU study reproductions.
- **Quick prototyping sugar (`benchkit.quick`)** for one-shot command-line
  benchmarks with minimal boilerplate.
- **CLI interface** (`benchkit` console script).
- **Wrappers & attachments:** `NiceWrap` (priority), trace-cmd wrapper +
  attachment, tcpdump attachment, signal/strace/llcstat/offcputime/klockstat
  eBPF attachments, Nsight profiling (nsys/ncu), differential flamegraphs,
  perf flamegraph fetching, `numactl --membind` option, perf-stat aggregation
  on hybrid x86.
- **Communication & devices:** UART communication layer, OpenOCD flasher
  helper, ADB/HDC unified under a `CommunicationLayer`, HDC support, devices
  reorganised under `devices/`.
- **Utilities & helpers:** unified logging utilities, `BENCHKIT_HOME` env
  var, `git_init` / `git_apply_patches`, git submodule support,
  `fuseiso` mount helper, `fetchtools` (split from buildtools) with `tar`,
  `sed`, `curl`; `cpupower` governor/frequency/exception helpers;
  `AsyncProcess.kill()` and premature-exit checks; symlink-latest for
  campaigns; `predlinux` optional NUMA balance disabling.
- **Engine features:** filter step in cartesian-product campaigns,
  `CampaignSuite`-level dependency check, JSON serialization extension,
  pre-run hooks gain access to `other_variables`.
- **Charts:** lwchart callback to alter chart, log-scale catplot example.
- **Platform support:** minimal Darwin support; Nix flake.
- **Docs & infra:** benchmark/campaign documentation, RocksDB example +
  Ubuntu 24.04 notes, success-stories with paper references, README shields,
  GitHub Actions code-formatting workflow, ROADMAP additions.

### Changed

- Renamed `PerfReportWrap` to `PerfRecordWrap`.
- Decoupled Tilt from the legacy engine in `benchmark.py`.
- Extended `pretty` handling with categories; placed `thread_*` columns at
  the end of CSV output for readability.
- Centralised result/working directories and aligned LevelDB paths.
- Bumped `dat3m` to 4.2.0; refreshed pip dependencies and Nix package.
- Benchmark engine now passes the wrapper function to single runs.

### Fixed

- `compat/new2old`: correct `record_dir` and propagation of `other_variables`.
- `benchmark.py`: pretty-vars and taskset edge cases; ugly-to-pretty string
  mapping.
- `flasher/openocd`, `benches/willitscale`, `benches/speccpu2017`: make
  `parent_dir` / address optional where appropriate.
- `benches/leveldb`: include duration in results, add `--num` support.
- `klockstat` attachment now waits until the eBPF program is attached.
- `lscpu` parsing handles non-integer `socket(s)` values.
- Multiple users on the same host can now coexist under `/tmp/benchkit*`.
- `all_checks.sh` is macOS- and BSD-compatible.
- Robustness around log return codes (no exception on ignored returns).

## [0.0.1] - 2024-09-17

Release with a tag for the first release on pypi.

## 2024-01-26

Initial open-sourced version.
