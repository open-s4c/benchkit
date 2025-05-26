# Tutorial: Conway's Game Of Life

## Clone Conway's Game Of Life repo

```bash
cd tutorials/cgol-bench/
mkdir deps
cd deps
git clone https://github.com/Guido589/conway-game-of-life-parallel.git
git clone https://github.com/brendangregg/FlameGraph
cd FlameGraph
git checkout cd9ee4c4449775a2f867acf31c84b7fe4b132ad5
cd ../../../..
```

## Generate venv & configure it

```bash
cd tutorials/cgol-bench/
./configure.sh
cd ../..
```

## Run campaigns for Conway's Game Of Life benchmarks

```bash
cd tutorials/cgol-bench/
. ./venv/bin/activate

cd cpu
./campaign_cgol_throughput.py
./campaign_cgol_perf_stat.py
./campaign_cgol_flamegraph.py
./campaign_cgol_different_sizes.py

cd ../gpu
./campaign_cgol_throughput.py
./campaign_cgol_different_sizes.py
```
