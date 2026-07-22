# Tutorial: libvsync locks

> **Note:** this tutorial uses the legacy campaign API. It remains
> functional, and its migration to the new engine API is in progress.
> For examples using the current API, see the
> [ICPE 2026 reproduction artifact](https://github.com/softwarelanguageslab/icpe26-benchkit-ae).

## Clone libvsync repo

```bash
cd tutorials/libvsync-locks/microbench/
mkdir deps
cd deps
git clone https://github.com/open-s4c/libvsync.git
cd ../..
```

In the following we assume you are in the `libvsync-locks` directory.

## Generate venv, configure it and activate it

```bash
./configure.sh
. ./venv/bin/activate
```

## Run campaign of locks

```bash
./campaign_locks.py
```
