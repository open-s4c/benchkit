# Example: MySQL

## Clone MySQL repo

```bash
cd examples/mysql/
mkdir deps
cd deps/
git clone https://github.com/mysql/mysql-server.git
cd mysql-server/
git checkout mysql-8.0.28
git checkout -b tmp-mysql-bench
git apply ../../patch01-ubuntu-ssl.diff  # patch to enable open-ssl3 support on Ubuntu 22.04
git commit -a -m "OpenSSL3 patch from Ubuntu 22.04"
git apply ../../patch02-vsync-locks.diff  # patch to enable VSync locks in MySQL server
git add -A
git commit -m "Experiment with VSync locks"
cd ..
git clone https://github.com/akopytov/sysbench.git
cd sysbench/
git checkout 1.0.20
cd ../../../..
```

## Generate venv & configure it

```bash
cd examples/mysql/
./configure.sh
cd ../..
```

## Run campaign for MySQL benchmarks

```bash
cd examples/mysql/
. ./venv/bin/activate
./campaign_mysql.py
```
