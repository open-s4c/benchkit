# Example: RocksDB

## Clone RocksDB repo

```bash
cd examples/rocksdb/
mkdir deps
cd deps/
git clone https://github.com/facebook/rocksdb.git
cd rocksdb/
git checkout v8.5.3
cd ../../../..
```

## Generate venv & configure it

```bash
cd examples/rocksdb/
./configure.sh
cd ../..
```

## Run campaign for RocksDB benchmarks

```bash
cd examples/rocksdb/
. ./venv/bin/activate
./campaign_rocksdb.py
```
