# Volano

## Download VOLANO Benchmark
# For more information take a look at: https://www.volano.com/benchmarks.html#:~:text=The%20VOLANO%20Benchmark%2C%20also%20known,running%20the%20VOLANO%20chat%20server.

```bash
cd examples/volano/kit/
mkdir deps
cd deps
curl -O https://www.volano.com/files/volano_benchmark_2_9_0.class
java volano_benchmark_2_9_0 -o .
```

## Change config
```bash
nano sartup.sh
change Host = localhost
change Java to java localtion
chmod +x *.sh
cd ../../../../..
```


## Generate venv & configure it

```bash
cd examples/volano/kit
./configure.sh
cd ../../..
```

## Run campaign for VOLANO benchmarks

```bash
cd examples/volano/kit
. ./venv/bin/activate
python3 volano.py
```
