# Benchmarks

A benchmark is what will compile and run your code, using the variables given by the campaign.
Because each project needs to be compiled and ran differently, there is currently no benchmark implementation that can be used, for this reason you should always make a custom benchmark.

To make a custom benchmark you need to override the `Benchmark` class, and implement the required methods.
Below is an example implementation of a custom benchmark, for more info see [building](#Building the benchmark) and [running](#Running the benchmark).
```python
from benchkit.campaign import Benchmark
from benchkit.utils.dir import get_curdir
from benchkit.shell.shellasync import AsyncProcess

import pathlib
import shutil
from typing import Any, Dict, List


# The code that should be benchmarked is oftentimes relatively to the location of the current file, which can be gotten using the following method
_bench_src_path = get_curdir(__file__)
_build_dir = _bench_src_path / "build"

class MyBenchmark(Benchmark):
    # Init method, setup all of the required variables
    def __init__(
        self,
    ) -> None:
        # Init method, calls the `__init__` function of the `Benchmark` class
        super().__init__(
            # See [Command wrappers](https://github.com/open-s4c/benchkit/blob/main/docs/wrappers.md)
            command_wrappers=(),
            command_attachments=(),
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=(),
        )

    @property
    def bench_src_path(self) -> pathlib.Path:
        # Returns the path to the source code that needs to be benchmarked
        return _bench_src_path

    # Return all of the variables, given to the campaign, that are required to build the source code.
    # These are the only variables that will be given to the `build_bench` method.
    @staticmethod
    def get_build_var_names() -> List[str]:
        # TODO: Add your build variables here
        return ["importantBuildVariable", "importantVariable"]

    # Return all of the variables, given to the campaign, that are required to run the benchmark.
    # These are the only variables that will be given to the `single_run` method.
    @staticmethod
    def get_run_var_names() -> List[str]:
        # TODO: Add your run variables here
        return ["importantRunVariable", "importantVariable"]

    # Build the source code using the values required for the current experiment
    def build_bench(
        self,
        # The variables defined in `get_build_var_names`, which values are given by the campaign
        # TODO: Add your build variables (defined in  `get_build_var_names`) here.
        importantBuildVariable,
        importantVariable,
        # The constants given to the campaign
        constants,
        # Holds all of the variables that are given to this method, but not used
        **_kwargs,
    ) -> None:
        # Remove the build directory before rebuilding
        if _build_dir.is_dir() and len(str(_build_dir)) > 4:
            shutil.rmtree(str(_build_dir))

        # Create build directory
        self.platform.comm.makedirs(path=_build_dir, exist_ok=True)

        # The command used to compile the code, each argument should be its own string in the array.
        # e.g. To compile a single file using `gcc` this should be `["gcc", path_to_file]`
        # TODO: add your build command here
        compile_command = [ ]
        # Run the command inside of the build directory
        self.platform.comm.shell(
            command=compile_command,
            # The command is executed inside of the build directory
            current_dir=_build_dir,
        )

    # Run the benchmark once
    def single_run(
        self,
        # The variables defined in `get_run_var_names`, which values are given by the campaign
        # TODO: Add your run variables (defined in  `get_run_var_names`) here.
        importantRunVariable,
        importantVariable,
        # The constants given to the campaign
        constants,
        # Holds all of the variables that are given to this method, but not used
        **kwargs,
    ) -> str | AsyncProcess:
        # The command used to run the benchmark, each argument should be its own string in the array.
        # TODO: add your run command here
        run_command = [ ]

        # Run the benchmark in the build directory
        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=run_command,
            current_dir=_build_dir,
            environment=None,
            wrapped_environment=None,
            print_output=True,
        )
        return output

    # Parse the output from an experiment, and turn it into a dictionary, any information that is returned from this method will be added to the output `csv` file
    def parse_output_to_results(
        self,
        command_output: str,
        build_variables: Dict[str, Any],
        run_variables: Dict[str, Any],
        **kwargs,
    ) -> Dict[str, Any]:
        # This assumes that each experiments prints lines with the following format `<variable>=<value>`, delimited with `;`
        # e.g. `var1=5;var2="value for var2"`
        key_seq_values = command_output.strip().split(";")
        result_dict = dict(map(lambda s: s.split("="), key_seq_values))
        return result_dict
```
This benchmark can then be used for a [campaign](campaign.md).

> [!NOTE]
> The above is an, incomplete, example implementation that should be adapted to your own use case.
> To facilitate this, `TODO`s have been added where you should change the implementation of the class to fit your needs.

> [!NOTE]
> Because of the definition of `parse_output_results` this benchmarking class expects a single output line of `scv` code as extra information.
> If this is not what is outputted by your results, either change the output, or change the definition of `parse_output_to_results`.

## Building the benchmark

To build your benchmark code you have to implement the `get_build_var_names` and `build_bench` functions in your `Benchmark` class.

The `get_build_var_names` function should return a list of all of the variables that are used inside of the `build_bench` function.
The values for these variables will be supplied by the [campaign](campaign.md).

The `build_bench` function should compile your benchmarking code.
Note that this function will be called every time an experiment with different build variables (as defined by `get_build_var_names`) is started, this mean that you build folder might already contain some build artifacts and should be cleaned.

The `build_bench` function should compile your benchmarking code, and is called with the following arguments:
* `self`
    * the self of the class
* `benchmark_duration_seconds`
    * How long a single benchmark should take, or `None`
* `constants`
    * A dictionary containing the constants of your benchmark, this is given by the [campaign](campaign.md).
* The variables returned by `get_build_var_names`
    * These are the variables that vary between experiments, and are given by the [campaign](campaign.md).
If you don't need some of these variables, you can use the `**kwargs` which will contain all of the arguments that you do not specify inside of the function.

## Running the benchmark

To run your benchmark code you have to implement the `get_run_var_names` and `single_run` functions in your `Benchmark` class.

The `get_run_var_names` function should return a list of all of the variables that are used inside of the `single_run` function.
The values for these variables will be supplied by the [campaign](campaign.md).

The `single_run` function should run a single experiment, and return either the console output, or the asynchronous process if the program is ran asynchronously.

The `single_run` function should run your compiled benchmark code, and is called with the following arguments:
* `self`
    * the self of the class
* `benchmark_duration_seconds`
    * How long a single benchmark should take, or `None`
* `constants`
    * The constants for your benchmark, this is given by the [campaign](campaign.md).
* `build_variables`
    * The variables returned by `get_build_var_names`
* `record_data_dir`
    * The directory where the results of this experiment will be stored
* `other_variables`
    * The variables neither returned by `get_run_var_names` or by `get_build_var_names` 
* The variables returned by `get_run_var_names`
    * These are the variables that vary between experiments, and are given by the [campaign](campaign.md).
If you don't need some of these variables, you can use the `**kwargs` which will contain all of the arguments that you do not specify inside of the function.
