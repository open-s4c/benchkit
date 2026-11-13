// Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
// SPDX-License-Identifier: MIT

// GPU execution-budget calibration microbenchmark.
//
// Usage: taskspin <nb_jobs> <wcet_us> [<wcet_us> ...]
//
// For each task (one requested execution budget per argument), launch
// <nb_jobs> single-block kernels that spin on the GPU global timer for the
// requested duration, and time each job with CUDA events. Prints one line
// per task:
//
//   task=<i> requested_us=<c> mean_us=<m> max_us=<M>

#include <cstdio>
#include <cstdlib>

#include <cuda_runtime.h>

#define CHECK(call)                                                          \
    do {                                                                     \
        cudaError_t err_ = (call);                                           \
        if (err_ != cudaSuccess) {                                           \
            fprintf(stderr, "CUDA error %s at %s:%d\n",                      \
                    cudaGetErrorString(err_), __FILE__, __LINE__);           \
            exit(1);                                                         \
        }                                                                    \
    } while (0)

// Wall-clock nanoseconds. Unlike clock64() (SM cycles), the global timer does
// not depend on the SM clock frequency, which varies with DVFS/boost.
__device__ unsigned long long globaltimer_ns()
{
    unsigned long long t;
    asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(t));
    return t;
}

__global__ void spin(unsigned long long duration_ns)
{
    const unsigned long long start = globaltimer_ns();
    while (globaltimer_ns() - start < duration_ns) {
    }
}

static float time_job(unsigned long long duration_ns, cudaEvent_t begin, cudaEvent_t end)
{
    float elapsed_ms = 0.0f;
    CHECK(cudaEventRecord(begin));
    spin<<<1, 1>>>(duration_ns);
    CHECK(cudaGetLastError());
    CHECK(cudaEventRecord(end));
    CHECK(cudaEventSynchronize(end));
    CHECK(cudaEventElapsedTime(&elapsed_ms, begin, end));
    return elapsed_ms * 1000.0f;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <nb_jobs> <wcet_us> [<wcet_us> ...]\n", argv[0]);
        return 1;
    }
    const int nb_jobs = atoi(argv[1]);

    cudaEvent_t begin, end;
    CHECK(cudaEventCreate(&begin));
    CHECK(cudaEventCreate(&end));

    // Warm up: context creation and first-launch costs stay out of the data.
    time_job(1000, begin, end);

    for (int task = 0; task < argc - 2; ++task) {
        const double requested_us = atof(argv[task + 2]);
        const unsigned long long duration_ns = (unsigned long long)(requested_us * 1000.0);

        double sum_us = 0.0;
        double max_us = 0.0;
        for (int job = 0; job < nb_jobs; ++job) {
            const double job_us = time_job(duration_ns, begin, end);
            sum_us += job_us;
            if (job_us > max_us) {
                max_us = job_us;
            }
        }
        printf("task=%d requested_us=%.3f mean_us=%.3f max_us=%.3f\n",
               task, requested_us, sum_us / nb_jobs, max_us);
    }

    CHECK(cudaEventDestroy(begin));
    CHECK(cudaEventDestroy(end));
    return 0;
}
