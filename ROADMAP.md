# Roadmap

We list here the useful features and changes we are considering for the
future.

## Benchmarks to be supported

[ ] memcached
[ ] mariadb
[X] redis
[ ] dpdk
[ ] From "Thread Clustering: Sharing-Aware Scheduling on SMP-CMP-SMT Multiprocessors"
    [X] VolanoMark
    [ ] SPECjbb2013 (retired?)
    [ ] Rubis & MySQL
[ ] From "Coherence Stalls or Latency Tolerance: Informed CPU Scheduling for Socket and Core Sharing"
    [ ] SPEC-CPU 2017
    [ ] PARSEC
    [ ] GraphLab / TuriCreate (maybe retired)
    [ ] Singular Value Decomposition
        [ ] other graph benchmarks
        [ ] other machine learning and filtering applications
[ ] From "Thread-Placement Learning"
    [ ] Metis MapReduce
[ ] From "Online Thread Auto-Tuning for Performance Improvement and Resource Saving"
    [ ] NAS Parallel Benchmarks (https://www.nas.nasa.gov/software/npb.html)
    [ ] Ligra
    [ ] GAP
[ ] From "Pandia: comprehensive contention-sensitive thread placement"
    [ ] SPEC OMP 2012
[ ] From "OS Scheduling with Nest: Keeping Tasks Close Together on Warm Cores"
    [ ] TPC-H (on Postgres)
    [ ] Linux kernel compilation gcc benchmark
    [ ] Wired Tiger BTree benchmark
        [ ] FaceRec
        [ ] Graph500
    [ ] Hackbench
        [ ] DaCapo
[ ] PQC algorithms
    [ ] Kyber
        https://eprint.iacr.org/2019/489
        https://github.com/mupq/nttm4
        https://pq-crystals.org/
    [ ] Dilithium
[ ] MiBench suite
    https://ieeexplore.ieee.org/document/990739
[ ] Servo & web rendering framework
    - they use a lot of parallelism
    - many big stakeholders are interested (Google, Apple, Huawei)
    - it's also an embedded use case
    - we can show neutral numbers
[ ] LMbench
    - OS-specific benchmarks
    - used in Huawei OSDI'24 paper
    - ref: https://lmbench.sourceforge.net/why_lmbench.html

## Functional changes

- Parallel runner: allows to queue the benchmarks of a single campaign to
  execute them as fast as possible. With m CPUs, m benchmark instances
  can be running in parallel, and the other ones are queuing. This is useful
  for single-cpu simulation or model checking for example.
  To facilitate some experiments, we can also stop the whole thing once the
  first benchmark finishes.

- Generation of static HTML with charts: instead of generating PNG and PDF,
  we can generate a self-contained HTML page with an interactive graph,
  generated with plotly or altair for example.
  We could also have some functions to start from a CSV file or a pandas
  DataFrame.

- Aggregation of results over time: the CSV files of benchkit can be archived
  in a repository and then a chart can be generated with x-axis being time,
  y-axis being the aggregated performance, and the color being the different
  considered variants/platforms. The aggregation can be the geometric mean
  over all dimensions (e.g. threads).
  "On each platform, one pick a set of thread options, a set of campaigns
   (queue, map, etc), and a set of possible flags (LSE/LLSC/builtin, whatever
   else). Then one select which of these dimensions should be variants.
   Eg, LSE/LLSC/builtin. The rest is aggregated via geometric mean. So you get
   on a platform for each variant, a geometric mean measurement of the
   performance over the versions of the software."
  We can run that for every release of a library.

- Platform Identification: a small util that identifies exactly the platform
  on which you run the experiments: processor model, number of sockets,
  motherboard model, amount of ram, gpu model, etc.
  Some kind of summary like the info displayed when running the neofetch
  command. Some string that uniquely identifies the characteristics of the
  platform used; and then this can be used in further comparison.
  E.g.: MySQL sysbench performance is actually influenced by the total amount
  of RAM in the system, here is how the performance evolved across systems
  when increasing available RAM.

- Differential Performance Testing: to identify regression, we can add tools
  to make the comparison of repos or repo+patch easier. And integrate for
  example "Differential Flame Graphs" from Brendan Gregg.
  Developing tools that can show impact of "changes" (like software or
  hardware changes: removing a line in the code, changing the frequency,
  or executing in a docker container).

- Caching of results:
  skip *building* the benchmark if we can detect that all result records
  underlying the specific build are already in cache.

- `lwcharts` data filtering:
  add the capability to filter the dataframe; could be implemented with
  the callback function to process the dataframe.

- Linux capability:
  add a command wrapper to set a capability, for example allowing to do
  scheduling class changes (it would be for example:
  `sudo setcap cap_sys_nice=eip ./db_bench`).

- Generation of shell script to reproduce build & run:
  like in benchkit.sh but specific to the data point considered.
  It would be output in the data directory related to the associated
  record.

- Tracking shas & diffs in the data directory:
  instead of outputting just the sha of the current repository, we could
  have a "tracking version" file in the data directory where we put the
  sha of the main repo and all the subrepos recursively, plus the
  "git diff" in all the repos, such that one can track the complete set
  of changes when executing the benchmark.
  We can also add a "warning" in the CSV header in case of the directory
  is dirty. (for now we just have the sha but is not visible enough).

- Additional logging information:
  now that a data directory is available for each campaign, we can
  inflate a bit the logging information about the running system & its
  environment. We can for example have some static information (for all
  records) and some dynamic information (per record):
  - total amount of ram (static)
  - currently consumed amount of ram (and other resources, like IO,
    etc.) (dynamic)
  - load (3 numbers to give a few information about how it changed)
    (dynamic)
  - position of the RAM chips (static)
  Notice that some of these information could be optional.

## Non-functional changes

- Release as a pip package!

- Use standard logging instead of print() calls.

- Add `mypy` (https://mypy-lang.org/) in the list of checkers applied.

- Add end-to-end tests that are automated.

## Defects / Bugs / Change Requests

- Error handling is required for when the platform is not registered
  with benchkit and `even` cpu order is used:
  `nb_cache_partitions` can be `None` and the following line crashes:
  `cpus_per_cache_partitions = nb_cpus // nb_cache_partitions`

- Remove "max nb threads" limitation:
  remove the _max_nb_threads check that filter-out "invalid" parameter
  space. It made sense at VSync/CLoF papers time but now we want to
  investigate oversubscription.

- Split Json result file in data directory:
  for now, the json file contains the information dumped like a line of
  the CSV file. A better structure would be to at least split in 3
  different categories:
  - build variables (inputs)
  - run variables (inputs)
  - observational variables (the output metrics)
  Or maybe we don't need build/run split in the future (with the new
  organisation, TBD). But at least the idea is to split inputs from
  outputs in the json results file.

- Refactor CSV log header:
  now that there is a data directory, we can put a bit less (or more
  condensed) information in the header of the CSV and dump the
  multi-dimensional data in the data directory. For example, we can have
  a structured file with the platform information, telling:
  - processor type
  - ram chips
  - operating frequency (of each core)
  - deep hierarchy information (cache groups)
  - etc. (see `platforms/__init__.py` for inspiration)

- In multi-index groupby data structure, improve management of optional
  values and default values for the specification of records.

- Refactor shell_out function:
  they became too complex over time. A cleanup would be handy.

## Documentation

Better document the following:

- predictable platforms

- deep numa hierarchy

- remote benchmarking
