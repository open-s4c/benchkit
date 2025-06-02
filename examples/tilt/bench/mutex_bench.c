// Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
// SPDX-License-Identifier: MIT

#include <stdio.h>
#include <pthread.h>
#include <string.h>

#define THREAD_COUNT 8
#define BENCH_DURATION_SEC 10

#define IMPLICIT_INIT

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

static atomic_bool done = false;
static atomic_uint_fast64_t iterations_total = 0;

void* worker(void* arg) {
	uint64_t iterations_local = 0;
	while (!atomic_load_explicit(&done, memory_order_relaxed)) {
		pthread_mutex_lock(&lock);
		// Critical section
		// (could do something tiny like a counter or memory op)
		pthread_mutex_unlock(&lock);

		// Non-critical section
		// (sleep or dummy ops to simulate delay)
		++iterations_local;
	}
	atomic_fetch_add(&iterations_total, iterations_local);
	return NULL;
}

int main() {
    #if !defined(IMPLICIT_INIT)
    if (pthread_mutex_init(&lock, NULL) != 0) {
        printf("Mutex initialization failed\n");
        return 1;
    }
    #endif /* EXPLICIT_INIT */

	pthread_t threads[THREAD_COUNT];

	for (int i = 0; i < THREAD_COUNT; i++) {
		pthread_create(&threads[i], NULL, worker, NULL);
	}

	sleep(BENCH_DURATION_SEC);
	atomic_store(&done, true);

	for (int i = 0; i < THREAD_COUNT; i++) {
		pthread_join(threads[i], NULL);
	}

	printf("Total iterations: %lu\n", atomic_load(&iterations_total));
    pthread_mutex_destroy(&lock);

    return 0;
}
