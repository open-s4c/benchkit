# Tutorial: LevelDB

## Clone LevelDB repo

```bash
cd tutorials/leveldb-bench/
mkdir deps
cd deps/
git clone --recurse-submodules https://github.com/google/leveldb.git
cd leveldb/
git checkout 068d5ee1a3ac40dabd00d211d5013af44be55bea
git apply ../../patch.diff  # apply patch for benchstats, fairness, mutex init & fixed duration support
git add -u
cd ../../../..
```

## Generate venv & configure it

```bash
cd tutorials/leveldb-bench/
./configure.sh
cd ../..
```

## Run campaign for LevelDB benchmarks

```bash
cd tutorials/leveldb-bench/
. ./venv/bin/activate
./campaign_leveldb.py
```

There is also a campaign that uses the platform **stabilization**
features of `benchkit` (the `helpers/linux/predictable` folder).
To run it, run the following:

```bash
./campaign_leveldb_stable.py
```

Another possible use case is `perf` that can be used as a command wrapper to
collect performance monitoring information into the CSV file or the data
directory.
Here follow a campaign to showcase it (see the source code for more
information):

```bash
./campaign_leveldb_perf.py
```

Finally, `perf` can also be used to generate a flamegraph, useful to debug
the performance of specific records.
The flamegraph repository must be cloned first, then the following campaign
generates a flamegraph for each record (each "dot" in the generated graphs):

```bash
cd tutorials/leveldb-bench/deps/
git clone https://github.com/brendangregg/FlameGraph.git
cd FlameGraph/
git checkout cd9ee4c4449775a2f867acf31c84b7fe4b132ad5
cd ../..
./campaign_leveldb_flame.py
```

You can also try different VSync locks in LevelDB using tilt.
The steps:

```bash
cd examples/tilt/
mkdir -p deps/
cd deps/
git clone https://github.com/open-s4c/tilt.git
git clone https://github.com/open-s4c/libvsync.git
cd ../../../tutorials/leveldb-bench/
. ./venv/bin/activate
./campaign_leveldb_locks.py
```
