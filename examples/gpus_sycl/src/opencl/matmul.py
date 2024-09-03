import argparse
import pathlib
import time

import numpy as np
import pyopencl as cl

parser = argparse.ArgumentParser()
parser.add_argument("BLOCK_SIZE", type=int)

args = parser.parse_args()

kernel_file = pathlib.Path("./matmul.cl")
kernel = open(kernel_file).read()

context = cl.create_some_context(False)
queue = cl.CommandQueue(context, properties=cl.command_queue_properties.PROFILING_ENABLE)
program = cl.Program(context, kernel).build()

n = 1024
size = n * n

h_a = np.full(size, 1).astype(np.int32)
h_b = np.full(size, 2).astype(np.int32)
h_c = np.zeros(size).astype(np.int32)

d_a = cl.Buffer(context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=h_a)
d_b = cl.Buffer(context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=h_b)
d_c = cl.Buffer(context, cl.mem_flags.WRITE_ONLY, h_c.nbytes)

program.matmul.set_scalar_arg_dtypes([None, None, None, np.int32])
start_time = time.time()
local_size = int(args.BLOCK_SIZE)
print(local_size)
event = program.matmul(queue, (n, n), (local_size, local_size), d_a, d_b, d_c, np.int32(n))
event.wait()
elapsed = (event.profile.end - event.profile.start) / 1e6

cl.enqueue_copy(queue, h_c, d_c)
queue.finish()
stop_time = time.time()

print(f"kernel_time: {elapsed}\nduration: {(stop_time - start_time)*1000.0}")
