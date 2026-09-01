# Example: Rodinia


## Pull Rodinia 


```bash
mkdir -p deps
cd deps/
git clone git@github.com:JuliaParallel/rodinia.git
cd rodinia/
git checkout ec580f6
git apply ../../rodina-benchmark.patch 
cd openmp
make -j
cd ../data/bfs/inputGen/
make
./gen_dataset.sh
cd ../../heartwall/
make
cd ../lud/
make
cd ../../../../
```

## Generate venv & configure it

```bash
./configure.sh
. ./venv/bin/activate
```

## Speedup stacks

To run the speedup stack example, you need the following dependencies.

- LLVM 3.7.1 or newer, compiled with BPF support (default=on)
- Clang, built from the same tree as LLVM

```bash
# On Ubuntu 24.04
sudo apt install libc6-dev-i386 libc6-dev linux-headers-$(uname -r)

sudo apt install -y zip bison build-essential cmake flex git llvm libedit-dev \
  libllvm18 llvm-18-dev libclang-18-dev python3 zlib1g-dev libelf-dev libfl-dev python3-setuptools \
  liblzma-dev libdebuginfod-dev arping netperf iperf libpolly-18-dev
```
https://github.com/iovisor/bcc/blob/master/INSTALL.md#ubuntu---source

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
sudo setcap cap_sys_ptrace+ep $(which strace)
cd ../../..
```

The latest versions of strace on Ubuntu 24.04 contain a number of bugs.
If you encounter some of them please compile and install the latest strace version.

```bash
sudo apt update
sudo apt install git build-essential autoconf automake libtool \
                 pkg-config libunwind-dev
git clone https://github.com/strace/strace.git
cd strace
./bootstrap
./configure
make -j
sudo make install
```


Cloning and compiling the thread-profiler-bpf dependency

```bash
cd deps/
# git clone https://github.com/theodegeest/thread-profiler-bpf.git --recursive
git clone git@github.com:theodegeest/thread-profiler-bpf.git --recursive
cd thread-profiler-bpf/
make install
make -j
sudo setcap cap_sys_resource,cap_sys_admin+eip ./src/thread-profiler
sudo chmod -R a+r /sys/kernel/tracing/events/sched/sched_process_fork
sudo chmod -R a+r /sys/kernel/tracing/events/sched/sched_process_exit
# sudo chmod -R a+r /sys/kernel/tracing/events/syscalls/sys_enter_read
# sudo chmod -R a+r /sys/kernel/tracing/events/syscalls/sys_exit_read
sudo chmod -R a+r /sys/kernel/tracing/events/block/block_rq_issue
sudo chmod -R a+r /sys/kernel/tracing/events/block/block_rq_complete
sudo chmod -R a+r /sys/kernel/tracing/events/syscalls/sys_enter_futex
sudo chmod -R a+r /sys/kernel/tracing/events/syscalls/sys_exit_futex
cd ../..
```

Running the speedup stack campaign.
```
./campaign_rodinia.py
```

