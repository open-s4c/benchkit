# Tutorial: Tilt

## Clone libvsync and tilt repositories

```bash
cd examples/tilt/
cd deps/
git clone https://github.com/open-s4c/libvsync.git
git clone https://github.com/open-s4c/tilt.git
cd ../
```

## Generate venv & configure it

```bash
./configure.sh
. ./venv/bin/activate
```

## Run campaign for Reciprocating lock benchmarks

```bash
./campaign_tilt.py
```

## Todo

- [ ] Fix implemenation of CLH lock
- [ ] Fix implementation of the atomic benchmark
