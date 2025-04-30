# Example: The DaCapo Benchmark Suite

This suite contains the following benchmarks:

- avrora
- batik
- biojava
- cassandra
- eclipse
- fop
- graphchi
- h2
- jme
- jython
- kafka
- luindex
- lusearch
- pmd
- spring
- sunflow
- tomcat
- tradebeans
- tradesoap
- xalan
- zxing

> [!NOTE]
> `h2o` is not supported, due to missing resources

## Clone The DaCapo Benchmark Suite repository

```bash
cd examples/dacapobench/
```
Modify the last line of the `local.properties` file so that it points to your java 11 installation.
Once this is done you can continue.

```bash
./setup-deps.sh
```

IMPORTANT: before trying to build the suite:

1. Set your JAVA_HOME environment variable appropriately (it must be set and be consistent with the VM that will be used to build the suite).
If you set your JAVA_HOME to Java 8 all the benchmarks will work. (Some use java 11 and will use the location provided in `local.properties`).
```bash
export JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64/jre 
```
2. Create the local.properties file (using default.properties as a template)
```bash
sudo update-alternatives --config java # select java 11
```
3. Set jdk.11.home, in the local.properties, to point to a Java 11 installation.
```bash
sudo update-alternatives --config javac # select javac 11
```

## Generate venv & configure it

```bash
./configure.sh
. ./venv/bin/activate
```

## Run simple test campaign

```bash
./campaign_dacapobench.py
```
