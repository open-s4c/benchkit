# Example: RocksDB

## Clone RocksDB repo

```bash
cd examples/rocksdb/
mkdir deps
cd deps/
git clone https://github.com/facebook/rocksdb.git
cd rocksdb/
git checkout v8.5.3
cd ../../../..
```

## Generate venv & configure it

```bash
cd examples/rocksdb/
./configure.sh
cd ../..
```

## Run campaign for RocksDB benchmarks

```bash
cd examples/rocksdb/
. ./venv/bin/activate
./campaign_rocksdb.py
```

## Speedup stacks

```
# For Focal (20.04.1 LTS)
sudo apt install -y zip bison build-essential cmake flex git libedit-dev \
  libllvm12 llvm-12-dev libclang-12-dev python zlib1g-dev libelf-dev libfl-dev python3-setuptools \
  liblzma-dev arping netperf iperf

# For Hirsute (21.04) or Impish (21.10)
sudo apt install -y zip bison build-essential cmake flex git libedit-dev \
  libllvm12 llvm-12-dev libclang-12-dev python3 zlib1g-dev libelf-dev libfl-dev python3-setuptools \
  liblzma-dev arping netperf iperf

# For Jammy (22.04)
sudo apt install -y zip bison build-essential cmake flex git libedit-dev \
  libllvm14 llvm-14-dev libclang-14-dev python3 zlib1g-dev libelf-dev libfl-dev python3-setuptools \
  liblzma-dev libdebuginfod-dev arping netperf iperf

# For Lunar Lobster (23.04)
sudo apt install -y zip bison build-essential cmake flex git libedit-dev \
  libllvm15 llvm-15-dev libclang-15-dev python3 zlib1g-dev libelf-dev libfl-dev python3-setuptools \
  liblzma-dev libdebuginfod-dev arping netperf iperf libpolly-15-dev

# For Mantic Minotaur (23.10)
sudo apt install -y zip bison build-essential cmake flex git libedit-dev \
  libllvm16 llvm-16-dev libclang-16-dev python3 zlib1g-dev libelf-dev libfl-dev python3-setuptools \
  liblzma-dev libdebuginfod-dev arping netperf iperf libpolly-16-dev

# For Noble Numbat (24.04)
sudo apt install -y zip bison build-essential cmake flex git libedit-dev \
  libllvm18 llvm-18-dev libclang-18-dev python3 zlib1g-dev libelf-dev libfl-dev python3-setuptools \
  liblzma-dev libdebuginfod-dev arping netperf iperf libpolly-18-dev

# For other versions
sudo apt-get -y install zip bison build-essential cmake flex git libedit-dev \
  libllvm3.7 llvm-3.7-dev libclang-3.7-dev python zlib1g-dev libelf-dev python3-setuptools \
  liblzma-dev arping netperf iperf
```

```
cd deps/
git clone git@github.com:iovisor/bcc.git
cd bcc/
git checkout 7da5916622dc3a581e4c4adc3003e588657f66fa
git submodule update --init --recursive
git apply ../../libbpf-tools-fix-compile.patch
cd libbpf-tools/
make -j
cd ../../..
```
