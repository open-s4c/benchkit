/*
 * Copyright (C) 2023 Huawei Technologies Co.,Ltd. All rights reserved.
 * SPDX-License-Identifier: MIT
 */

#include <vsync/atomic.h>
#include <pthread.h>
#include <stdio.h>
#include <unistd.h>

#include <config.h> /* defines NB_THREADS, RUN_DURATION_SECONDS and lock_* operations and types. */

static vatomic32_t must_stop;
static lock_t lock;
static unsigned long long shared_counter;

void* run_thread() {
    unsigned long count = 0u;

    while (!vatomic32_read(&must_stop)) {
        lock_acquire(&lock);
        count++;
        shared_counter++;
        lock_release(&lock);
    }

    void* result = (void*) count;
    return result;
}

int main() {
    unsigned long thread_counts[NB_THREADS];
    unsigned long global_count = 0u;

    vatomic32_init(&must_stop, 0);
    lock_init(&lock);

    pthread_t pthreads[NB_THREADS];
    for (size_t k = 0u; k < NB_THREADS; ++k) {
        pthread_attr_t pthread_attr;
        pthread_attr_init(&pthread_attr);
        pthread_create(&pthreads[k],
                       &pthread_attr,
                       run_thread,
                       NULL);
        pthread_attr_destroy(&pthread_attr);
    }

    sleep(RUN_DURATION_SECONDS);
    vatomic32_write(&must_stop, 1);

    for (size_t k = 0u; k < NB_THREADS; ++k) {
        void* return_value;
        pthread_join(pthreads[k], &return_value);
        thread_counts[k] = (long) return_value;
        global_count += thread_counts[k];
    }

    printf("global_count=%lu;duration=%u;nb_threads=%u",
           global_count, RUN_DURATION_SECONDS, NB_THREADS);
    for (size_t k = 0u; k < NB_THREADS; ++k) {
        printf(";thread_%zu=%lu", k, thread_counts[k]);
    }
    printf("\n");

    return 0;
}
