# Example: Will it Scale

## Clone Will it Scale repo

```bash
cd examples/willitscale/
mkdir deps
cd deps/
git clone https://github.com/antonblanchard/will-it-scale.git
cd will-it-scale/
git checkout a34a85cc1e9b9b74e94fdd3ecc479019da610e6a
git apply ../../patch.diff  # apply patch for WARMUP_ITERATIONS as a benchmark parameter
git add -u
cd ../../../..
```

## Generate venv & configure it

```bash
cd examples/willitscale/
./configure.sh
cd ../..
```

## Run campaign for Will it Scale benchmarks

```bash
cd examples/willitscale/
. ./venv/bin/activate
./campaign_willitscale.py
```
