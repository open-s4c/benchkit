# Tutorial: libvsync locks

## Clone libvsync repo

```bash
cd tutorials/libvsync-locks/microbench/
mkdir deps
cd deps
git clone <libvsync-repo-url> libvsync
# TODO git checkout <tag>
cd ../../../..
```

## Generate venv & configure it

```bash
cd tutorials/libvsync-locks
./configure.sh
cd ../..
```

## Run campaign of locks

```bash
cd tutorials/libvsync-locks
. ./venv/bin/activate
./campaign_locks.py
```
