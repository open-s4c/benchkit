# Tutorial: libvsync locks

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
