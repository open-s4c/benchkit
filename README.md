# benchkit: Performance Evaluation Framework

`benchkit` provides a push-button end-to-end performance evaluation
pipeline, which includes platform stabilization, benchmark configuration
& build, and an execution engine capable of exploring the specified
parameter space of the problem.

Around a given benchmark, the user can define a set of experiments
called **a campaign**.  Running the campaign within `benchkit` allows to
run the defined experiments, collect results, aggregate them, and
visualize the different variables and how they affect the overall system
performance. `benchkit` provides additional tools for fine grain
performance debugging and monitoring.


## Main principles

The project was born from the need to apply a systematic method to
evaluate computer systems. Indeed, the landscape of benchmarks is really
heterogeneous: each benchmark program tends to define its own
performance metrics and its own way of configuring, compiling, running
and collecting results. In addition, there is a great deal of duplicated
efforts occurring when a researcher or a programmer is generating charts
and tables to communicate results.

Performance evaluation and benchmarks are typically conducted when one
wishes to understand how their software is performing, by comparing
different variant implementations of the same interface or API (possibly
together with other variables). In that context, `benchkit` provides a
method to conduct benchmarks that is simple, efficient and extensible,
raising the abstraction level of how one thinks about performance
evaluation, and allows to design a set of experiments to gain knowledge
on the observed system.

In `benchkit`, the programmer defines a set of `campaigns` attached to a
`benchmark`. Each of these campaigns will explore a `parameter space`
that defines all the values that will be explored for each variable of
the `benchmark`. A campaign script define the variables and the
parameter space, allowing the experiment to be reproducible, as the
specification of the benchmark campaigns is _source code_, making it
self-documenting, executable, reproducible, and easily shareable with
other programmers.

The `benchkit` flow is illustrated by the following figure:
```
                     Benchmark
                         |
                         ▼
                  ┌─────────────┐
  Parameters ────▶│ Campaign Run│────────────────▶ Build
                  └───────┬─────┘            ▲       ▼
                          │   │              │──▶── Run
                          │   ▲              ▲       ▼
                          │   └────────◀─────└─◀── Collect
                          │
                          ▼
                  ┌─────────────┐                               ┌───────────────┐
                  │ CSV Results │ ─▶ Filter, Aggregate, Plot ─▶ │ Chart, Report │
                  └─────────────┘                               └───────────────┘
```

`benchkit` is ideally suited for the following use cases:
- investigating a performance issue in an application, a design, a data
  structure, etc.;
- getting precise, reliable and reproducible measurements;
- running custom benchmark programs;
- running common or existing benchmark programs;
- visualizing different dimensions of the studied problem;
- reproduce the results of a prior measurement and tracking the hidden
  parameters (OS version, compiler version, operating frequency, etc.);
- reduce the variance of experiment results.

In summary, it allows to tackle the high complexity of performance
evaluation initiatives.

`benchkit` allows to avoid common pitfalls like "the bash scripts of
death", unstable or unreproducible results, uncontrolled configuration,
undocumented environment (OS version, compiler version, etc.). It
provides a unified approach to save datasets holding both the experiment
results and the configuration of the environment. It optionally
generates data visualization for the stored results. It reduces the
duplication efforts and provides tooling allowing to set up a
performance regression pipeline for applications.

`benchkit` increases credibility and confidence in the results, enables
a tighter feedback loop allowing for an easy "fix and retry" flow.
Eventually, automating and running campaigns of experiment allow
programmers to gain a deeper knowledge of how their systems perform and
lead to curated insights captured with less time.

The approach is lightweight in the sense that `benchkit` can support any
benchmark by plugging it in the engine.

A **campaign** of experiments is composed of:
- a set of **variables** to observe;
- the **values** to explore for these variables;
- **one** benchmark to run.

A **benchmark** defines methods to do the following:
- configure the benchmark;
- build the benchmark;
- perform a single run of the benchmark experiment;
- collect the result of this single run.
The build & run steps takes variables as input whose values can be
defined at the **campaign** level.

Once assembling the campaign with its benchmark, `benchkit` will then
iterate over the variables and their values using the cartesian product
(or other supported or custom methods), run the benchmark and output the
results in a format that is friendly with plotting tools.


## Getting Started

Without further ado, let us fix the idea by using tutorials.
The repository provides different implementations called
[examples](examples/), including locktorture, postgresql and rocksdb.
We also provide what we call "[tutorials](tutorials/)", which are more
extensive examples and also include the whole execution and scripting
infrastructure.

### Tutorial 1: simple evaluation of VSync spinlocks

The first tutorial uses `benchkit`'s sibling project: `libvsync`.
We provide a simple client code that benchmarks various VSync
spinlocks, and use it in a benchkit campaigns with various contention
levels (i.e. number of threads).

The campaign evaluates the throughput of different spinlock
implementations defined in `libvsync` using a small microbenchmark,
similar to the "client code" test cases used when model checking the
code. The explored parameter space is composed of different spinlock
variants and contention levels (i.e. number of threads).
See the [README](tutorials/libvsync-locks/README.md) of the libvsync
lock tutorial for more information of how to run that campaign.

### Tutorial 2: LevelDB benchmark

We evaluate [LevelDB](https://github.com/google/leveldb), a well-known
key-value store engine. We use the benchmarks defined in the source code
of LevelDB. To run the campaigns, follow the instructions in the
[README](tutorials/leveldb-bench/README.md) of the LevelDB tutorial.


## How to design experiments

Within `benchkit`, designing experiments require to articulate a
campaign.

The first step is **to define the parameter space**, by defining:
- **what is varying?** For example, the number of threads, varying
  algorithm implementations, build options.
  This defines the **variables**
- **what is the values for each variable?** List the different
  **values** you want each variable to take.
- **how to iterate over the multiple variables?** Do you use the
  cartesian product? Do you have a list of records defining
  variable-values? Do you want a custom way of exploring the space?

`benchkit` provides various types of support for parameter space
exploration according to the chosen `Campaign` type.

The second step is to **choose or implement a benchmark**.
A benchmark is always composed of 3 steps: (1) configure, (2) build and
(3) run. The variables defined in the parameter space can be used as
parameters of the build and run. `benchkit` provides an API for
a benchmark to defines these 3 steps.

Campaigns are initialized with **one** benchmark. The benchmark can be
seen as a moving part that can be interchanged if the parameters are
compatible (see the figure above).
In the future, a campaign might support running several benchmarks,
either in parallel or in sequence.

In summary, a **campaign of experiments** is
**1 benchmark + N variables**.
Once ran, it provides a dataset of results (in a unified CSV format,
also documenting the environment in comments in the header) and
associated visualizations.

The reason to articulate campaigns is the following: it is our
contention that this exercise help to **raise the abstraction level** of
how to think about benchmarks. When thinking about parameter space,
compatible benchmarks and campaign results, it offers a new perspective
that leads to better understanding and gained knowledge. It allows to
easily generate new information that the user can exploit, navigate,
discuss and build upon. It also allows to write experiments to answer
performance questions on specific platforms, like for example:
- what is the real impact/cost of adding an atomic to collect run-time
  concurrent statistics?
- what is better: protecting a sequential data structure with a lock or
  use a lock-free version of the same data structure? In what situation
  is it better? According to different payloads (e.g. high contention,
  oversubscription, fastpath, etc.)?

The user can build a campaign to answer each of these questions. Writing
campaigns is a quick method to obtain that level of information for the
platform used.


## Reproducible research

`benchkit` enables users to evaluate their designs predictably: once the
campaign script is written, the reproducibility of results is inherently
supported: the user just needs to re-run the campaign script.

By stabilizing platforms (using `benchkit` extensions) and scripting the
campaigns, reproducible research can be attained.


## Supported benchmarks

The following lists the benchmarks supported by `benchkit`:

- Leveldb
- Rocksdb
- Kyoto cabinet TODO
- benchmarksql
- sysbench (MySQL, postgres)
- Locktorture (Linux kernel)
- Will-it-scale TODO
- STREAM TODO

We will add more in the future, so stay tuned!
Also, contributions are welcome, so if you added the support for an
existing benchmark or your own custom benchmark, feel free to submit it
for review by the `benchkit` [maintainer](MAINTAINERS).


## High-level source organization

The source code of this repository is organized as follows:
```
benchkit
├── benchkit            core directory of the framework
│   ├── adb                 automation of ADB (Android Debug Bridge)
│   ├── benchmark.py        engine for running evaluations
│   ├── campaign.py         model experiments, parameter space, and results
│   ├── charts              plotting tools, depending on matplotlib & pandas
│   ├── commandwrappers     wrappers to extend benchmark commands
│   ├── communication       channels (shell, file system) between host & local/remote targets (phones, ssh, etc.)
│   ├── dependencies        encode dependencies (packages, binaries) of benchmarks
│   ├── helpers             various helper features to automate routine tasks (e.g. building Linux build, sending SQL queries, etc.)
│   ├── lwchart.py          light-weight way to generate charts after experiments (with pandas & seaborn)
│   ├── platforms           encode all information about servers & various target machines
│   ├── remote              allow running remote experiment using tmux
│   ├── sharedlibs          shared libraries to load when running benchmark to customize executions (e.g. LD_PRELOAD)
│   ├── shell               functions to call shell synchronously & asynchronously
│   └── utils               misc functions to assist with directories, gdb, network, etc.
├── examples            directly usable examples of benchmarks using the benchkit
│   ├── benchmarksql        support for benchmarsql payload for a SQL DBMS server
│   ├── kyotocabinet        support for kyotocabinet benchmark
│   ├── leveldb             support for the benchmarks of the key-value store
│   ├── locktorture         support for the so called kernel module
│   ├── mysql               support for MySQL DBMS in benchkit with sample campaign (using sysbench)
│   ├── postgresql          support for postgres DBMS in benchkit with sample campaign (using sysbench)
│   ├── rocksdb             support for rocksdb benchmark
│   ├── stream              support for STREAM benchmark
│   ├── sysbench            support for sysbench, payload of a DBMS SQL server
│   └── willitscale         support for Will-it-Scale benchmark
├── plotbench           webgui to display results (independent from benchkit but draw from CSV results)
├── scripts             various helper scripts
├── tests               pytests
└── tutorials           guides to learn how to use the benchkit
    ├── leveldb-bench       running a campaign that runs LevelDB benchmarks
    └── libvsync-locks      running a campaign that evaluates VSync locks
```


## Success Stories

`benchkit` has been used to evaluate the performance of system software
in 3 published papers [1,2,3], 6 Huawei internal projects, and allowed
to obtain 4 SIGOPS badges of reproducible research. It has also been
used to provide some performance evidence on the Linux Kernel Mailing
List [4].

[1] [Push-Button Verification and Optimization for Synchronization Primitives on Weak Memory Models. ASPLOS'2021.](https://dl.acm.org/doi/10.1145/3445814.3446748)

[2] [Verifying and Optimizing the HMCS Lock for Arm Servers. NETYS'2021.](https://dl.acm.org/doi/10.1007/978-3-030-91014-3_17)

[3] [CLoF: A Compositional Lock Framework for Multi-level NUMA Systems. SOSP'2021.](https://dl.acm.org/doi/10.1145/3477132.3483557)

[4] [lock_torture results for different patches. LKML, 2023.](https://lkml.org/lkml/2023/3/1/603)


## Contributing

Contributions to `benchkit` are welcome.  See the
[developer guide](CONTRIBUTING.md) for details.


## License

`benchkit` is released under the [MIT License](LICENSE).


## Acknowledgement

This project is under the support of [OpenHarmony Concurrency & Coordination TSG (Technical Support Group), 并发与协同TSG][tsg].
[tsg]: https://www.openharmony.cn/techCommittee/aboutTSG
