# Getting started

## Installation

You can install this framework using [pypy](https://pypi.org/project/pybenchkit/):
```bash
pip install pybenchkit
```

## Getting started

In order to run a benchmark, you need a [campaign](campaign.md), and you need a [benchmark](benchmark.md).
Once you have those two things, you can use these to run your benchmark in the following way.

```python
from benchkit.campaign import CampaignCartesianProduct

def runCampaign():
    # Define the campaign, here `CampaignCartesianProduct` is used, but you can also use your own campaign
    campaign = CampaignCartesianProduct(
        name="benchmark",
        # Create a new `benchmark` class, you should add your own here.
        benchmark=Benchmark(),
        # How many times every experiment should be repeated
        nb_runs=3,
        variables={
            # Vary the amount of threads that is used
            "nb_threads": [2, 4, 8],
        },
        # Variables that can be used in your benchmark, but always remain constant
        constants={},
        debug=False,
        gdb=False,
        enable_data_dir=False,
        pretty={},
    )
    # Run the campaign
    campaign.run()
```

This will create a new campaign and run it, the results of this campaign will then be stored in the `results` folder.
If you also want the data plotted you can do this by running `campaign.generate_graph(plot_name="name")`, this graph will then also be placed in the `results` folder.
Generating this graph does, however, require some extra Python libraries, these can be installed using the following command:
```python
pip install matplotlib pandas seaborn
```
For more info about how to use campaigns, and their arguments, see [campaign](campaign.md).

### Running the benchmark

To run the benchmark you have to simple call the python file in an environment where all of the dependencies have been this can, assuming that you python file is called `benchmark.py`, you can start your benchmarks using the following command:
```bash
python benchmark.py
```
