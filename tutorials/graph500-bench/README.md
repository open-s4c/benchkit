# Tutorial: Graph500

## Clone Graph500 repo

```bash
cd tutorials/graph500-bench/
mkdir deps
cd deps
git clone https://github.com/graph500/graph500.git
cd graph500/
git checkout f89d643ce4aaae9a823d310c6ab2dd10e3d2982c
git apply ../../patch.diff  # apply patch for multiple definition error, see https://github.com/graph500/graph500/issues/38#issuecomment-1439097398
git add -u
cd ../../../..
```

## Generate venv & configure it

```bash
cd tutorials/graph500-bench/
./configure.sh
cd ../..
```

## Run campaign for Graph500 benchmarks

```bash
cd tutorials/graph500-bench/
. ./venv/bin/activate
./campaign_graph500.py
```
