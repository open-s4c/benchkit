# GPU benchmark in a pythainer container

A complete, modern benchkit campaign that runs a CUDA microbenchmark inside a
GPU-enabled container built with [pythainer](https://github.com/apaolillo/pythainer).

The workload is a typical first step for GPU real-time experiments:
random task sets are drawn with **UUniFast-Discard**, and for each task the
GPU executes jobs of the requested WCET; the campaign measures how accurately
the GPU honors those execution budgets (`measured / requested`).

## Layout

| File | Role |
|---|---|
| `campaign_tasksets.py` | The campaign: parameter space, container, plot. Run this. |
| `taskspin.py` | The benchmark: a plain class with `fetch/build/run/collect`. |
| `tasksets.py` | UUniFast-Discard task-set generation (seeded, reproducible). |
| `container.py` | pythainer image + benchkit platform running commands in the container. |
| `src/taskspin.cu` | CUDA microbenchmark: spin jobs of given durations, time them. |

## Prerequisites

- An NVIDIA GPU, its driver, and the NVIDIA container toolkit
  (`docker info | grep nvidia` lists the runtime).
- benchkit's virtualenv with `pythainer` installed.

## Run

```sh
./campaign_tasksets.py --quick   # 2 records, smoke test
./campaign_tasksets.py           # 45 records: nb_tasks x utilization x seed
```

The first run builds the image `benchkit-gpu-tasksets` (CUDA 12.6 devel base);
later runs reuse docker's cache.

## Output

Everything lands in `results/`:

```
results/
  benchmark_<host>_gpu_tasksets_<date>.csv     one row per record
  benchmark_<host>_gpu_tasksets_<date>/
    metadata.json                              git revision, kernel, durations
    benchkit-<date>-01.{png,pdf}               the plot
    nb_tasks-2/total_utilization-0.5/seed-0/run-1/
      taskset.json                             the generated task set
      per_task.csv                             per-task measurements
      experiment_results.json                  the record: inputs + outputs
```

CSV columns are prefixed with their role (`input/nb_tasks`,
`output/worst_ratio`, ...); plotting helpers strip the prefixes, so plots
refer to plain names (`x="total_utilization"`).

## How the pieces fit

- **Benchmark** (`taskspin.py`): no base class. Step parameters are bound by
  name from the campaign variables (`run(ctx, nb_tasks, total_utilization,
  seed, nb_jobs=20)`). Commands go through `ctx.exec`; the steps' Python code
  runs on the host. Per-record artifacts go into `ctx.record_dir`, and
  `collect()` returns one record (aggregates) per run.
- **Container** (`container.py`): `ctx.exec` runs each command in a fresh
  `docker run --rm` of the image, with the GPU attached. The example directory
  is mounted at the *same absolute path* inside the container, so build
  directories and record directories need no path translation.
- **Campaign**: `CampaignCartesianProduct` explores the cartesian product of
  the variables, one record per point, through benchkit's execution engine.

## Adapting it

- Replace `src/taskspin.cu` and the `run()`/`collect()` bodies with your own
  tool; keep generating inputs from the record's variables (here, the seed),
  so every record is reproducible from its CSV row.
- Add CUDA tools or libraries to the image in `gpu_builder()`.
- Pick any other plot: `generate_graph` forwards its arguments to seaborn.
