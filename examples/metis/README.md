# Example: Metis

## Links

- [Metis](http://pdos.csail.mit.edu/metis/)
- [Github repo](https://github.com/ydmao/Metis.git)

## Setup

### Clone Metis repo

```bash
cd examples/metis/
mkdir deps
cd deps/
git clone https://github.com/ydmao/Metis.git
cd Metis
git apply ../../patch.diff  # apply patch for missing architectures
cd ../..
```

### Generate venv & configure it

In the following we assume you are in the `metis` directory.

```bash
./configure.sh
. ./venv/bin/activate
```

### Configure project

In the following we assume you are in the `metis` directory.

To configure and build the project

```bash
cd deps/Metis/
./configure
make
```

To link with a specific memory allocator

```bash
cd deps/Metis/
./configure --with-malloc=<jemalloc|flow>
make clean
make
```

## Available benchmarks

After setup, the following benchmarks work out of the box:

- `wrmem`
- `kmeans`
- `pca`
- `matrix_mult`

The following benchmarks require extra data files:

- `hist`
- `linear_regression`
	-
	- sometimes fails with "Segmentation fault" (mistake in the Metis benchmark code)
- `string_match`
- `wc`
- `wr`

Assuming we are in the `metis` directory, download the data files:

```bash
cd deps/Metis/
wget http://pdos.csail.mit.edu/metis/data2.tar.gz
```

Unpack the test data files:

```bash
tar -xvzf data2.tar.gz
```

This will create a `data` folder.

## Run campaign with all benchmarks

In the following we assume you are in the `metis` directory.

```bash
./campaign_metis.py
```
