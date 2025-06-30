import shlex
import time
from pathlib import Path
from typing import List, Optional
from benchkit.shell.command_execution.io.hooks.hook import IOHook, IOWriterHook, OutputHook
from benchkit.shell.command_execution.io.stream import ReadableIOStream, WritableIOStream


def debugger_hook(command:str,hooklocation:str) -> IOWriterHook:
    def time_accurate() -> float:
        return time.time()

    def command_folder() -> str:
        return str(int(time_accurate())) + str(abs(hash(command)))

    def tag_bytes_with_time( byt:bytes) -> bytes:
        offset = time_accurate()
        return f'{offset},'.encode("utf-8") + byt


    def hook_function(input_stream:ReadableIOStream,output_stream:WritableIOStream) -> None:
        start_time = time_accurate()
        output_file_path = Path(f"./.commandlogging/{command_folder()}/{hooklocation}")
        output_file_path.parent.mkdir(exist_ok=True, parents=True)
        with open(output_file_path, "bw+", buffering=0) as output_file:
            output_file.write('hookstart,command,location\n'.encode("utf-8"))
            output_file.write(f'{time.time()},{command},{hooklocation}\n'.encode("utf-8"))
            byt = input_stream.read_line()
            while byt:
                output_stream.write(byt)
                output_file.write(tag_bytes_with_time(byt))
                byt = input_stream.read_line()
            output_file.write('hookend\n'.encode("utf-8"))
            output_file.write(f'{time_accurate() - start_time}'.encode("utf-8"))

    return IOWriterHook(hook_function)

def add_logging_hooks(ordered_input_hooks:Optional[List[IOHook]], ordered_output_hooks:Optional[List[OutputHook]],command:List[str]):
    new_ordered_input_hooks:List[IOHook] = []
    a = 0
    location = "after_initial_input"
    if ordered_input_hooks:
        for x in ordered_input_hooks:
            new_ordered_input_hooks.append(debugger_hook(shlex.join(command),location + f'-{a}-in'))
            new_ordered_input_hooks.append(x)
            location = x.name
            a += 1
    new_ordered_input_hooks.append(debugger_hook(shlex.join(command),location))

    a = 0
    err_location = "after_comand"
    out_location = "after_comand"
    new_ordered_output_hooks:List[OutputHook] = []

    if ordered_output_hooks:
        err_log:Optional[IOWriterHook] = debugger_hook(shlex.join(command),err_location + f"-{a}-err")
        out_log:Optional[IOWriterHook] = debugger_hook(shlex.join(command),out_location + f"-{a}-out")
        new_ordered_output_hooks.append(OutputHook(out_log,err_log))
        for y in ordered_output_hooks:
            err_log = None
            out_log = None
            if y._std_err_hook:
                err_location = y._std_err_hook.name
                err_log = debugger_hook(shlex.join(command),err_location + f"-{a}-err")
            if y._std_out_hook:
                out_location = y._std_out_hook.name
                out_log = debugger_hook(shlex.join(command),out_location + f"-{a}-out")

            new_ordered_output_hooks.append(y)
            new_ordered_output_hooks.append(OutputHook(out_log,err_log))
            a += 1
    return (new_ordered_input_hooks, new_ordered_output_hooks)
