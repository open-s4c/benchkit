# Command wrappers

You can also wrap a [benchmark](benchmark.md) in another command, this can be
useful if you want to reuse a certain tracing command, without
having to redefine it every time.

To use a wrapper, you have to create your benchmark with the given
wrapper that you want to do, this can be accomplished by, when using
the example code given in [benchmark](benchmark.md), changing to `init` function to the
following:
```python
def __init__(
    self,
) -> None:
    # TODO: Add wrappers to this array
    wrappers = []
    super().__init__(
        # The wrappers that should be used for this command
        command_wrappers=wrappers,
        command_attachments=(),
        shared_libs=(),
        # See [Benchmark hooks](https://github.com/open-s4c/benchkit/blob/main/docs/hooks.md)
        pre_run_hooks=(),
        post_run_hooks=(),
    )
```
This will include the wrappers in your benchmark, for more info about the wrappers
that are included into bechnkit see [Included wrappers](#Included wrappers).

Adding the wrappers to your benchmark will not run them as your benchmark defines
how it should be ran, to run the benchmark with the wrappers you have to change the
`singe_run` function to use the included wrappers:
```python
# `single_run` method, see [benchmarks](https://github.com/open-s4c/benchkit/blob/main/docs/benchmark.md#Running the benchmark) for more info
def single_run(
    self,
    **kwargs
) -> str | AsyncProcess:
    # TODO: add your run command here
    run_command = [ ]

    # Load the environment, this is determined by the wrappers you have added
    environment = self._preload_env()
    # Wrap your command with the wrappers you added to your benchmark
    wrapped_run_command, wrapped_environment = self._wrap_command(
        run_command=run_command,
        environment=environment,
        **kwargs,
    )

    # Run the wrapped command
    output = self.run_bench_command(
        run_command=run_command,
        # NOTE: Add the wrapped command here
        wrapped_run_command=wrapped_run_command,
        current_dir=_build_dir,
        environment=environment,
        # NOTE: Add the wrapped environment here
        wrapped_environment=wrapped_environment,
        print_output=True,
    )
    return output
```

Running this will, for most campaigns, create a new file containing the data gathered
by the wrapper, if you want to also add this data to the output `csv` file, or add it in a
graph see [hooks](hooks.md).

> [!NOTE]
> Most wrappers require `enable_data_dir` to be set to `True` in your [campaign](campaign.md)

## Included wrappers

### perf

Runs the [`perf`](https://perf.wiki.kernel.org) Linux utility on your benchmark.
This wrapper can be created in the following way:
```python
from benchkit.commandwrappers.perf import PerfStatWrap, PerfReportWrap

perfStatWrap = PerfStatWrap(events=["cache-misses"])
perfReportWrap = PerfReportWrap()
```

There are two versions of the `perf` wrapper, `PerfStatWrap` will wrap
you command with the `perf stat` command, while `PerfReportWrap` will
wrap your command with `perf record` and `perf report`.

When using `PerfStatWrap`, you should also pass the `events` argument,
<!--TODO: link to PMU events-->
this argument decides with [PMU]() events `perf` should record.

`PerfStatWrap` has the following [hooks](hooks.md):
* `post_run_hook_update_results`

`PerfReportWrap` has the following [hooks](hooks.md):
* `post_run_hook_flamegraph`
* `post_run_hook_report`

### ltrace

Runs [ltrace](https://www.ltrace.org/).
This wrapper can be created in the following way:
```python
from benchkit.commandwrappers.ltrace import LtraceWrap

ltraceWrap = LtraceWrap()
```

### numactl

Runs [numactl](https://github.com/numactl/numactl).
This wrapper can be created in the following way:
```python
from benchkit.commandwrappers.numactl import NumactlWrap

numactlWrap = NumactlWrap(membind=membind, local_alloc=local_alloc)
```

### strace

Run strace
This wrapper can be created in the following way:
```python
from benchkit.commandwrappers.strace import StraceWrap

straceWrap = StraceWrap()
```

### taskset

Runs taskset.
This wrapper can be created in the following way:
```python
from benchkit.commandwrappers.taskset import TasksetWrap

tasksetWrap = TasksetWrap()
```

### tracecmd

Runs [tracecmd](https://www.trace-cmd.org/).
This wrapper can be created in the following way:
```python
from benchkit.commandwrappers.tracecmd import TraceCmdWrap

tasksetWrap = TraceCmdWrap()
```

### valgrind

Runs [valgrind](https://valgrind.org/).
This wrapper can be created in the following way:
```python
from benchkit.commandwrappers.valgrind import ValgrindWrapper

valgrindWrapper = ValgrindWrapper()
```

### env

Adds the environment variables, defined in the wrapped environment, to the command
This wrapper can be created in the following way:
```python
from benchkit.commandwrappers.env import EnvWrap

envWrap = EnvWrap()
```
