# Volano

## Download VOLANO Benchmark

For more information, please visit [Volano website](https://www.volano.com/benchmarks.html).


```bash
sudo apt update && sudo apt install -y openjdk-21-jre-headless
cd examples/volano/
mkdir deps
cd deps
curl -O https://www.volano.com/files/volano_benchmark_2_9_0.class
java volano_benchmark_2_9_0 -o .
```

## Change config
```bash
nano startup.sh
change Host = localhost
change Java to java localtion
chmod +x *.sh
cd ../../..
```


## Generate venv & configure it

```bash
cd examples/volano/
./configure.sh
cd ../..
```

## Run campaign for VOLANO benchmarks

```bash
cd examples/volano/
. ./venv/bin/activate
./benchmark_volano.py
```
