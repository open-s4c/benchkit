// Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
// SPDX-License-Identifier: MIT

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <sched.h>
#include <unistd.h>

#define OPS_PER_LOOP 10

// Return time in seconds with nanosecond precision
static double now_sec() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <duration_seconds> <cpu_core_id>\n", argv[0]);
        return 1;
    }

    double duration = atof(argv[1]);
    int core_id = atoi(argv[2]);

    if (duration <= 0) {
        fprintf(stderr, "Please provide a positive duration.\n");
        return 1;
    }

    if (core_id < 0) {
        fprintf(stderr, "Please provide a valid (non-negative) CPU core ID.\n");
        return 1;
    }

    // Set CPU affinity
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core_id, &cpuset);

    if (sched_setaffinity(0, sizeof(cpuset), &cpuset) != 0) {
        perror("sched_setaffinity failed");
        return 1;
    }

    volatile uint64_t dummy = 0;
    uint64_t ops = 0;
    double start = now_sec();
    double end = start + duration;

    while (now_sec() < end) {
        // Unrolled loop to increase ops per iteration
        dummy += 1; dummy *= 2; dummy ^= 0xDEADBEEF;
        dummy += 3; dummy *= 4; dummy ^= 0xBAADF00D;
        dummy += 5; dummy *= 6; dummy ^= 0xCAFEBABE;
        dummy += 7; dummy *= 8; dummy ^= 0x8BADF00D;
        ops += OPS_PER_LOOP;
    }

    double elapsed = now_sec() - start;

    // Use dummy so it's not optimized away
    fprintf(stderr, "Final dummy value: %lu\n", dummy);
    printf("Operations performed: %lu\n", ops);

    return 0;
}
