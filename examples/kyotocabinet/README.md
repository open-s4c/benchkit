# Example: Kyoto Cabinet

## Clone Kyoto Cabinet repo

```bash
cd examples/kyotocabinet/
mkdir deps
cd deps/
wget --continue https://dbmx.net/kyotocabinet/pkg/kyotocabinet-1.2.76.tar.gz
tar -xf kyotocabinet-1.2.76.tar.gz
cd kyotocabinet-1.2.76/
git init && git add -A && git commit -m "Vanilla 1.2.76"
git apply ../../patches/01-cloudflare.diff && git add -A && git commit -m "Cloudflare"
git apply ../../patches/02-cloudflare.diff && git add -A && git commit -m "Cloudflare (new files)"
git apply ../../patches/03-benchmark.diff && git add -A && git commit -m "Add benchmark"
git apply ../../patches/04-benchkit.diff && git add -A && git commit -m "Benchkit glue"
cd ../../../..
```

## Generate venv & configure it

```bash
cd examples/kyotocabinet/
./configure.sh
cd ../..
```

## Run campaign for Kyoto Cabinet benchmarks

```bash
cd examples/kyotocabinet/
. ./venv/bin/activate
./campaign_kyotocabinet.py
```

Another possible use case is `perf` that can be used as a command wrapper to
collect performance monitoring information into the CSV file or the data
directory:

```bash
./campaign_kyotocabinet_perf.py
```

Finally, `perf` can also be used to generate a flamegraph, useful to debug
the performance of specific records.
The flamegraph repository must be cloned first, then the following campaign
generates a flamegraph for each record (each "dot" in the generated graphs):

```bash
cd examples/kyotocabinet/deps/
git clone https://github.com/brendangregg/FlameGraph.git
cd FlameGraph/
git checkout cd9ee4c4449775a2f867acf31c84b7fe4b132ad5
cd ../..
./campaign_kyotocabinet_flame.py
```

You can also try different VSync locks in Kyoto Cabinet using tilt.
The steps:

```bash
cd examples/tilt/
mkdir -p deps/
cd deps/
git clone https://github.com/open-s4c/tilt.git
git clone https://github.com/open-s4c/libvsync.git
cd ../../../examples/kyotocabinet/
. ./venv/bin/activate
./campaign_kyotocabinet_locks.py
```