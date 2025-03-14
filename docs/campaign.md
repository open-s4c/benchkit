# Campaigns

A campaign is the thing that runs your [benchmark](benchmark.md), a single campaign will run a single benchmark, but run it multiple times, using different build- and runtime-variables.

Inside of `benchkit` there are already three campaigns implemented, below all three of these are explained

The first of the campaigns is called `CampaignCartesianProduct`, will run an experiment for all sets of values for the variables, gotten when the Cartesian product is taken.
This mean that each combination of values will be tested, using this campaign.
For example, if you have the variables `var1` which can equal `1` or `2` and the variable `var2` which can equal `3` or `4`, you will get experiments with the following values.
```
var1 = 1; var2 = 3
var1 = 1; var2 = 4
var1 = 2; var2 = 3
var1 = 2; var2 = 4
```
This kind of campaign can be useful when you want to test every possible combination of values, but it can make the amount of experiments grow very large.

The second kind of campaign is the `CampaignIterateVariables`, will run an experiment for every pre-defined set of values for the given variables.
This gives you a larger amount of control over the variables that will be combined, ensuring that the amount of experiments ran will not grow too large, even when using a large amount of variables.

The last campaign is the `CampaignSuite`, this is a campaign that wraps other campaigns, instead of directly running experiments.
This campaign takes multiple other campaigns, of any sort, and will run them, one after another.
Note that, since `CampaignSuite` itself is not a subclass of `Campaign`, you cannot create a `CampaignSuite` that will run other `CampaignSuite`s.

## Creating a campaign

Creating a `CampaignCartesianProduct` and a `CampaignIterateVariables` can be done in very similar ways, because the two campaigns only differ in the way that they treat their variables, for this reason we will explain creating the two of them at the same time.

```python
from benchkit.campaign import CampaignCartesianProduct

campaign = CampaignCartesianProduct(
    # The name of your benchmark
    name="benchmark_name",
    # The benchmark to use
    benchmark=Benchmark(),
    # The amount of times each experiment should be ran
    nb_runs=3,
    # The variables that should be used for the experiments, this is the only thing that
    # differs between `CampaignCartesianProduct` and `CampaignIterateVariables` 
    variables={ },
    # This is a variable that remains constant throughout all of the experiments that are
    # ran in this campaign
    constants={"importantConstant": 5},
    # Wether or not debugging should be turned on, the actual implementation of the debugging
    # is handled by the benchmark
    debug=False,
    # Wether or not gdb should be used, the way how gdb is used is handled by the benchmark
    gdb=False,
    # Wether to enable data directories for this campaign, see [results](#results) for more info
    enable_data_dir=False,
    # How to pretty print variables, this will replace certain variable values with more meaningful,
    # values. This is only used to print certain variables in different ways.
    pretty={"importantVaryingVariable": {5: "five", 6: "six"}},
    ## Optional variables
    # Can be used to limit the length that an experiment is allowed to run, actually limiting the
    # experiment length should be implemented by the benchmark.
    benchmark_duration_seconds = None, # Set to e.g. 5.
    # 
    continuing = False
)
```

The above code snippet shows you how to initialize a campaign, the only thing that differs between `CampaignCartesianProduct` and `CampaignIterateVariables` is the `variables` argument.

For `CampaignCartesianProduct` this argument requires a dictionary where each variable that should vary is assigned an array with all of its possible values.
```python
variables = {
    "var1": [1, 2, 3],
    "var2": [4, 5, 6],
    "var3": ["very", "important", "values"]
}
```
Using this dictionary for the variables in `CampaignCartesianProduct` will run `27` experiments, combining the three variables in every possible way.

For `CampaignIterateVariables` this argument requires an array of dictionaries, each assigning a value to all of the values that can vary.
```python
variables = [
    {
        "var1": 1,
        "var2": 5,
        "var3": "very",
    },
    {
        "var1": 2,
        "var2": 5,
        "var3": "important",
    },
    {
        "var1": 2,
        "var2": 4,
        "var3": "values",
    }
]
```
Using this array for the variables in `CampaignIterateVariables` will run `3` experiments, each one using one dictionary to assign a value to every variable.

Create a `CampaignSuite` can be done by initializing it with a list of campaigns.
```python
from benchkit.campaign import CampaignSuite

# Add your campaigns here
campaigns = [...]
suite = CampaignSuite(campaigns = campaigns)
```
This will create a new `CampaignSuite` that will run all of the campaigns inside of `campaigns` when ran.

## Running a campaign

To run a campaign, you call the `run` method on that campaign.
```python
campaign.run()
```

If you want to run a campaign suite, you call the `run_suite` method on that suite.
```python
suite.run_suite()
```
This method also accepts a `parallel` argument, this is `false` by default, but when set to `true` the different campaigns inside of the suite will be ran in parallel.
```python
suite.run_suite(parallel=True)
```

You can also call the method `print_durations` on a suite to ensure that, while running, the time it took to run an experiment, and the expected time required to finish the campaign suite will be printed to the terminal.

## Results

When running a benchmark, all of the results will be put into the `results` folder.
When `enable_data_dir` is disabled, all files will be placed directly into the this folder, otherwise each campaign will get its own folder, and in those folders each variable and run will also be given their own folder with more information about that particular run.

The results are placed inside of `csv` files, with information stored about the system and benchmark configuration as comments, and the actual results stored as data inside of the `csv`.
This can look like the following

### Graphs

`benchkit` also allows you to make graphs from the data that is collected.
To do this you can run `generate_graph` on a finished campaign, or `generate_graphs` on a campaign suite to create a graph for each campaign, both of these methods take the same arguments.
Calling `generate_graph` on a campaign suite will generate a graph using the combined results of all the campaigns inside of the suite.

> [!NOTE]
> When making graphs, you are required to enable data directories, this can be done by setting `enable_data_dirs` to `True` when creating the campaign, for more info see [results](#Results).

These functions only require a `plot_name` as an argument, which is the name of the [`seaborn`](https://seaborn.pydata.org/) plot that should be generated.
Afterwards you can pass optional arguments accepted by [`seaborn`](https://seaborn.pydata.org/), if the value of these arguments is the name of one of your variables (as [given](#Creating a campaign)) then `benchkit` will automatically give the correct values for that variable to [`seaborn`](https://seaborn.pydata.org/).
This can be seen in the following example:
```python
suite.generate_graphs(plot_name="lineplot", x="nb_threads", y="duration", hue="elements");
```
This example will generate a [line plot](https://seaborn.pydata.org/generated/seaborn.lineplot.html) for every campaign in the given suite where the `x`-axis contains the amount of threads used, the `y`-axis the time it took to finish the experiment, and a different line will be created, with a different color, for each value of the variable `elements`.

If you want to generate a different plot after finishing your experiments, without rerunning them, you can use the `generate_chart_from_single_csv` function.
This function takes the same arguments as `generate_graph` but with the following extra arguments:
* `csv_pathname`
    * Type: `PathType`
    * The path to the `CSV` file from which it can read the data
* `output_dir`
    * Type: `PathType`
    * Default: `"/tmp/figs"`
    * The directory in which it should place the new graph
* `prefix`
    * Type: `str`
    * Default: `""`
    * A prefix for the name of the generated file, the eventual filename will be `f"benchkit-{prefix}{timestamp}-{figure_id}.png"`
* `nan_replace`
    * Type: `bool`
    * Default: `True`
    * If `True`, replace all the `None`s in the data with `NaN`
* `process_dataframe`
    * Type: `DataframeProcessor`
    * Default: `identical_dataframe`
    * A function that can modifies the dataframe before using it

This means you can generate a new graph, based on a given benchmark file without
having to rerun your experiment using the following code:
```python
from benchkit.lwchart import generate_chart_from_single_csv

generate_chart_from_single_csv(
    "results/<benchmark file>.csv",
    plot_name="histplot",
    prefix="important_experiment-"
    output_dir="results/",
)
```
Note that, this graph will not include the name of the campaign that was run,
if you want to add this you have to set the `prefix` argument.
