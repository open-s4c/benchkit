# Benchmark hooks

Hooks are functions that will be called before or after every experiment of a [benchmark](benchmark.md).
This is often used by [wrappers](wrappers.md) to change the way your program is going to run,
or to change the output of your [benchmark](benchmark.md) to include the output of what the
wrapper has added.
Any hook that is added to a [benchmark](benchmark.md) will be ran automatically
by benchkit.

To use a hook, you have to create your benchmark with the hooks that you want to add,
this can be accomplished by changing the `init` function to the following, assuming
you are starting from the example code given in [benchmark](benchmark.md):
```python
def __init__(
    self,
) -> None:
    # TODO: Add hooks to these arrays
    pre_run_hooks = []
    post_run_hooks = []
    super().__init__(
        # See [Benchmark wrappers](https://github.com/open-s4c/benchkit/blob/main/docs/benchmark.md)
        command_wrappers=(),
        command_attachments=(),
        shared_libs=(),
        # Add the hooks here
        pre_run_hooks=pre_run_hooks,
        post_run_hooks=post_run_hooks,
    )
```
To give an example, below is how you would add the `perf` [wrapper](wrappers.md#perf),
with one of its hooks:
```python
from benchkit.commandwrappers.perf import PerfStatWrap

def __init__(
    self,
) -> None:
    perfStatWrap = PerfStatWrap(events=["cache-misses"])
    # This will add the results of `perf` to the final results outputted by benchkit
    post_run_hooks = [perfStatWrap.post_run_hook_update_results]

    super().__init__(
        command_wrappers=[perfStatWrap],
        command_attachments=(),
        shared_libs=(),
        pre_run_hooks=(),
        post_run_hooks=post_run_hooks,
    )
```

## Pre-run hooks

A pre-run hook is a function that is called before running the actual experiment,
with all of the variables that are used in your campaign.

## Post-run hooks

A post-run hook is a function that is called after running the experiment,
with the results of the experiment, and the data folder.
If the hook returns a dictionary, the values in this dictionary will be added
to the results of your benchmark and will therefore be added to the final `CSV`
file, and you will be able to use their values in [graphs](campaign.md#graphs).
