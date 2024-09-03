import argparse
import pathlib
import time

import numpy as np
import pyopencl as cl

parser = argparse.ArgumentParser()
parser.add_argument("BLOCK_SIZE", default=1024, type=int)

args = parser.parse_args()
print("BLOCK SIZE: ", args.BLOCK_SIZE)

kernel_file = pathlib.Path("./add.cl")
kernel = open(kernel_file).read()

context = cl.create_some_context(False)  # noninteractive
queue = cl.CommandQueue(context, properties=cl.command_queue_properties.PROFILING_ENABLE)
program = cl.Program(context, kernel).build()

h_a = np.full((1 << 25,), 1.0).astype(np.float32)
h_b = np.full((1 << 25,), 2.0).astype(np.float32)

d_a = cl.Buffer(context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=h_a)
d_b = cl.Buffer(context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=h_b)

program.add.set_scalar_arg_dtypes([None, None])
start_time = time.time()
event = program.add(queue, h_a.shape, (args.BLOCK_SIZE,), d_a, d_b)
event.wait()
elapsed = (event.profile.end - event.profile.start) / 1e6


cl.enqueue_copy(queue, h_b, d_b)
queue.finish()
stop_time = time.time()

print(f"kernel_time: {elapsed}\nduration: {(stop_time - start_time)*1000.0}")
