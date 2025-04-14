# Tutorial: lusearch

## Clone The DaCapo Benchmark Suite repository

```bash
cd examples/lusearch/
mkdir deps/
cd deps/
git clone git@github.com:dacapobench/dacapobench.git 
cd ../
```

## Generate venv & configure it

```bash
./configure.sh
. ./venv/bin/activate
```

## Run simple test campaign

```bash
./campaign_lusearch.py
```
