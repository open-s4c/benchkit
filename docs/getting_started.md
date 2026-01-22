# Getting started

## Installation

You can install this framework using [pypy](https://pypi.org/project/pybenchkit/):
```bash
pip install pybenchkit
```

## Getting started

> [!IMPORTANT]
> The `benchkit.quick` is not available in version 0.0.1 as it was added in commit `32077d5`, if you a version prior to this commit you should use make a [benchmark](benchmark.md) and a [campaign](campaign.md)

In order to run a simple benchmark, you can use the `quick_cmd_campaign` function, this function creates a simple benchmark and allows you to run it.

```python
from benchkit.quick import quick_cmd_campaign

def dd_cmd(optpt):
    return f"dd if=/dev/zero of=/tmp/tempfile bs={optpt['bs']} count={optpt['count']}"

optspace = {
    "bs": ["4K", "16K", "64K"],
    "count": [1000, 5000, 10000],
}

if __name__ == "__main__":
    campaign = quick_cmd_campaign("dd_disk_io", optspace, dd_cmd, nb_runs=3)
```
In this case, the `campaign` variable will hold a normal [campaign](campaign.md), to run it and get results from it see [Running a campaign](campaign.md#Running a campaign) and [Results](campaign.md#Results).

The `quick_cmd_campaign` function accepts the following arguments:
* `name`
    * Type: 'str'
    * The name of your benchmark
* `options`
    * Type: `Dict[str, List[Any]]`
    * The options that your benchmark should use, using a Cartesian product of all of the given options, as described in [Creating a campaign](campaign.md#Creating a campaign).
* `benchmark`
    * A function that takes all of your options, and returns the string of the command that will be ran.
* `nb_runs`
    * Type: `int`
    * default: `1`
    * The amount of runs that each experiment should be ran.

Here is an example to benchmark `dd` with two options

> [!NOTE]
> Using `benchkit.quick` is only possible for simple benchmarks as it misses a lot of options, for more complex benchmarks, you should make a [benchmark](benchmark.md) and a [campaign](campaign.md).

### Running the benchmark

To run the benchmark you have to simple call the python file in an environment where all of the dependencies have been this can, assuming that you python file is called `benchmark.py`, you can start your benchmarks using the following command:
```bash
python benchmark.py
```
