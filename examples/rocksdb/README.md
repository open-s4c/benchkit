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

To run the speedup stack example, you need the following dependencies.

- LLVM 3.7.1 or newer, compiled with BPF support (default=on)
- Clang, built from the same tree as LLVM


Cloning and compiling the libbpf-tools dependencies.
```
cd deps/
git clone git@github.com:iovisor/bcc.git
cd bcc/
git checkout 7da5916622dc3a581e4c4adc3003e588657f66fa
git submodule update --init --recursive
git apply ../../libbpf-tools-fix-compile.patch
cd libbpf-tools/
make -j
sudo setcap cap_sys_resource,cap_sys_admin+eip ./klockstat
sudo setcap cap_sys_resource,cap_sys_admin+eip ./offcputime
sudo setcap cap_sys_resource,cap_sys_admin+eip ./llcstat
sudo setcap cap_sys_ptrace+ep /usr/bin/strace
cd ../../..
```

Running the speedup stack campaign.
```
./campaign_rocksdb_speedup_stacks.py
```


One shot from benchkit root to speedup stack example (for development)

```
sudo -v
while true; do sudo -v; sleep 60; done &
cd examples/rocksdb/
mkdir deps
cd deps/
git clone https://github.com/facebook/rocksdb.git
cd rocksdb/
git checkout v8.5.3
cd ../../../..
cd examples/rocksdb/
./configure.sh
cd ../..
cd examples/rocksdb/
. ./venv/bin/activate
cd deps/
git clone git@github.com:iovisor/bcc.git
cd bcc/
git checkout 7da5916622dc3a581e4c4adc3003e588657f66fa
git submodule update --init --recursive
git apply ../../libbpf-tools-fix-compile.patch
cd libbpf-tools/
make -j
sudo setcap cap_sys_resource,cap_sys_admin+eip ./klockstat
sudo setcap cap_sys_resource,cap_sys_admin+eip ./offcputime
sudo setcap cap_sys_resource,cap_sys_admin+eip ./llcstat
sudo setcap cap_sys_ptrace+ep /usr/bin/strace
kill %1
cd ../../..
./campaign_rocksdb_speedup_stacks.py
```


Cleanup of capabilities

```
sudo setcap -r /usr/bin/strace
```
