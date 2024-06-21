# Conway's Game Of Life
## Cloning Conway's Game Of Life and benchkit

```sh
$ git clone --recurse-submodules https://github.com/Guido589/conway-game-of-life-parallel.git
```

## Running the campaigns

```sh
$ cd conway-game-of-life-parallel/benchkit/tutorials/cgol-bench
$ ./configure.sh
$ . ./venv/bin/activate
$ cd cpu
$ ./campaign_cgol_throughput.py
$ ./campaign_cgol_perf_stat.py
$ ./campaign_cgol_flamegraph.py
$ ./campaign_cgol_different_sizes.py
$ cd ../gpu
```