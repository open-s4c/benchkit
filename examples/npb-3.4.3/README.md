# Example: NPB

## Clone NPB repo

```bash
cd examples/npb-3.4.3/
./clone.sh
cd ../..
```

## Generate venv & configure it

```bash
cd examples/rocksdb/
./configure.sh
cd ../..
```


## Run campaign for NPB benchmarks

```bash
cd examples/rocksdb/
. ./venv/bin/activate
./campaign_npb.py
```
