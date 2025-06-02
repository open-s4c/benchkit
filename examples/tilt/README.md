# Tilt

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

## Campaigns

### Simple Mutex test

Runs a simple campaign to run Tilt locks.

```bash
./campaign_test.py
```

### Reciprocating lock benchmarks

Runs a campaign that runs the benchmarks described in the Reciprocating Locks paper, using the Tilt.

```bash
./campaign_reciprocating_locks.py
```

## Todo

- [ ] Fix implemenation of CLH lock
- [ ] Fix implementation of the atomic benchmark
