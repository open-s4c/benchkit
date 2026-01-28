# Tutorial: Tilt

## Clone libvsync and tilt repositories

```bash
cd examples/tilt/
mkdir deps/
cd deps/
git clone https://github.com/open-s4c/libvsync.git
git clone https://github.com/open-s4c/tilt.git
cd libvsync
git checkout v4.0.2
cd ../tilt
git checkout v2.1.0
cd ../..
```

## Generate venv & configure it

```bash
./configure.sh
. ./venv/bin/activate
```

## Run simple test campaign

```bash
./campaign_tilt.py
```
