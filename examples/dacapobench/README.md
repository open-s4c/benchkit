# Example: The DaCapo Benchmark Suite

## Clone The DaCapo Benchmark Suite repository

```bash
cd examples/dacapobench/
mkdir deps/
cd deps/
git clone git@github.com:dacapobench/dacapobench.git 
cd dacapobench/benchmarks/
cp default.properties local.properties
```

IMPORTANT: before trying to build the suite:

1. Set your JAVA_HOME environment variable appropriately (it must be set and be consistent with the VM that will be used to build the suite).
2. Create the local.properties file (using default.properties as a template)
3. Set jdk.11.home, in the local.properties, to point to a Java 11 installation.

## Generate venv & configure it

```bash
./configure.sh
. ./venv/bin/activate
```

## Run simple test campaign

```bash
./campaign_dacapobench.py
```
