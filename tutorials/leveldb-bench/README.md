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
cd tutorials/leveldb-bench/
. ./venv/bin/activate
./campaign_leveldb_stable.py
```
