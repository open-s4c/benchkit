# GPU Scheduling and libsmctrl

NVIDIA GPUs consist of multiple GPC (General Processing Clusters) which contain
16 TPC (Thread Processing Clusters) containing each 2 SM (Streaming
Multiprocessors).
Using `libsmctrl`, it is possible to partition kernels across separate GPC and
TPC.
This means 2 concurrently running kernels do not compete for computation time on
the same SM.
This benchkit campaign serves to benchmark and analyze the scheduling behavior
of NVIDIA GPUs using this library.
This campaign is based on the
[rtas23](https://www.cs.unc.edu/~jbakita/rtas23)
and
[rtas24](https://www.cs.unc.edu/~jbakita/rtas24)
papers and their respective artifact evaluations
[rtas23-ae](https://www.cs.unc.edu/~jbakita/rtas23-ae)
and
[rtas24-ae](https://www.cs.unc.edu/~jbakita/rtas24-ae).

## Necessary Dependencies and Hardware
This campaign can only be run under certain circumstances.
The necessary dependencies and hardware for these circumstances are detailed
below.

### Dependencies
- Any standard Linux kernel should work
    - This campaign was tested on Void Linux with kernel versions
      4.19.304_1, 5.15.161_1, and 6.6.46_1.
- Benchkit and its dependencies
    - Installed by running configure.sh
- Docker
    - The benchmarks run in a docker container with a predetermined version of
      CUDA.
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
    - This is necessary for GPU passthrough of docker to work.
- An NVIDIA driver version inferior to 535.129.03 and superior to 450.80.02
    - This campaign was tested on driver version 470.239.06

The NVIDIA driver requirements are not hard requirements and can potentially
change.
The upper bound driver is 535.129.03 because `libsmctrl` does not implement SM
masking for CUDA versions greater than 12.1 as those versions use a larger mask
in order to support larger GPUs.
The lower bound driver is determined by the CUDA version used in the Docker
container, which is 11.4.3.
The
[support matrix](https://docs.nvidia.com/deeplearning/cudnn/latest/reference/support-matrix.html)
and
[cuda compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/contents.html)
web pages contain information on which CUDA versions are compatible with which
drivers.
All CUDA docker containers can be found on
[docker hub](https://hub.docker.com/r/nvidia/cuda/tags).
If you want to change the CUDA version and/or driver version you are using, make
sure to check these URLs.
Another potential problem is compute capabilities: depending on the driver
version and CUDA version some compute capabilities may no longer work.
More information about compute capabilities can be found in the
[CUDA documentation](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#compute-capabilities).
As such changing drivers or CUDA versions means it is also necessary to modify the Makefile of
[cuda_scheduling_examiner](https://github.com/JoshuaJB/cuda_scheduling_examiner_mirror).

### Modifying the Makefile
To modify the Makefile of `cuda_scheduling_examiner`, follow these steps.

Clone the repository using the following command.
```sh
git clone https://github.com/JoshuaJB/cuda_scheduling_examiner_mirror.git -b rtas23-ae
```

In the `Makefile`, modify lines 8 and 15 through 23 as necessary and create a
patch file.
```sh
git diff > cuda_scheduling_examiner_mirror_makefile.patch
```

Place this patch file in the `patches` directory of this campaign.
This patch should automatically be applied.

### Hardware
Currently, only NVIDIA GPUs of the following architecture are supported.

- Kepler
- Maxwell
- Pascal
- Volta
- Turing
- Ampere

This campaign was ran on an NVIDIA RTX 3060, which uses the Ampere architecture.


## Running the Campaign
In order to run this campaign follow these steps.

```sh
./configure.sh
source ./venv/bin/activate
./campaign_libsmctrl.py
```

### Variables
The following build variables are available:

- **kernel_names**: The names of the kernels to execute (excluding the file
  extension),
- **cthread_counts**: The number of CUDA threads to use for each kernel,
- **block_counts**: The number of CUDA blocks to use for each kernel,
- **additional_infos**: The additional info provided to each kernel,
- **release_times**: The time at which the kernels should be released
  respectively,
- **sm_masks**: The SM masks that should be used for each kernel respectively,
- **iterations**: The number of iterations that should be performed.

Besides iterations, all of these variables can consist of a list of tuples.
This is because a configuration can run multiple kernels at once.
These kernels may need to be given different parameters.
The following configuration illustrates this.

```python
variables={
    "kernel_names": [("timer_spin", "timer_spin")],
    "cthread_counts": [(1024,1024)],
    "block_counts": [(20,8)],
    "additional_infos": [(250000000,250000000)],
    "release_times": [(0, 0.1)],
    "sm_masks": [("0xffffffffffffffe0","0xfffffffffffff01f")],
    "iterations": [1],
},
```

In this configuration, a single config is generated.
This config executes 2 "timer_spin" kernels with each 1024 CUDA threads.
The first kernel runs on 20 CUDA blocks while the second runs on only 8.
The second kernel is also released 0.1 seconds later than the first.
The SM masks also differ across the 2 kernels.

In case an array is to be provided to a kernel, the array should be expressed as
a tuple as well.
The following code shows an example of this.

```python
variables={
    ...
    "cthread_counts": [((32,32),(32,32))],
    ...
},
```

This specifies 2 multidimensional thread counts for 2 separate kernels in 1
configuration.

### Adding New Variables
In order to add a variable to the config generator it must be added to the
variables dictionary and build variables list.
The file `generate_config.py` should be modified to use the new variable when
generating a configuration JSON.

## Links
- [libsmctrl](http://rtsrv.cs.unc.edu/cgit/cgit.cgi/libsmctrl.git/)
- [cuda_scheduling_examiner](https://github.com/JoshuaJB/cuda_scheduling_examiner_mirror)
- [nvdebug](http://rtsrv.cs.unc.edu/cgit/cgit.cgi/nvdebug.git)
