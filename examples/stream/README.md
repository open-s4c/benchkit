# Example: STREAM

## Clone STREAM repo

```bash
cd examples/stream/
mkdir deps
cd deps/
git clone https://github.com/jeffhammond/STREAM.git
cd STREAM/
git checkout 4dbce1d0fdb7410e8f21b48f3381bc0a1341967f
git apply ../../patch.diff  # apply patch for WARMUP_ITERATIONS as a benchmark parameter
git add -u
cd ../../../..
```

## Generate venv & configure it

```bash
cd examples/stream/
./configure.sh
cd ../..
```

## Run campaign for Will it Scale benchmarks

```bash
cd examples/stream/
. ./venv/bin/activate
./campaign_stream.py
```
