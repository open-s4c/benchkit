// Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
// SPDX-License-Identifier: MIT

#include <stdio.h>
#include <pthread.h>
#include <string.h>
#include <atomic>
#include <random>
#include <chrono>
#include <iostream>
#include <vector>
#include <thread>
#include <config.h> /* defines NB_THREADS, RUN_DURATION_SECONDS */

#define IMPLICIT_INIT

pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

struct S {
	uint32_t a, b, c, d, e;
};
std::atomic<S> shared;
std::atomic<bool> done{false};
std::atomic<uint64_t> iterations_total{0};

void* worker(void* arg) {
	S local = {1, 2, 3, 4, 5};
	uint64_t iterations_local = 0;
	while (!atomic_load_explicit(&done, std::memory_order_relaxed)) {
		pthread_mutex_lock(&lock);
		// Critical section
		atomic_exchange_explicit(&shared, local, std::memory_order_seq_cst); // exchange with global

		pthread_mutex_unlock(&lock);

		// Non-critical section
		// (sleep or dummy ops to simulate delay)
		++iterations_local;
	}
	atomic_fetch_add_explicit(&iterations_total, iterations_local, std::memory_order_relaxed);
	return NULL;
}

int main() {
    #if !defined(IMPLICIT_INIT)
    if (pthread_mutex_init(&lock, NULL) != 0) {
        printf("Mutex initialization failed\n");
        return 1;
    }
    #endif /* EXPLICIT_INIT */

	// Initialize shared atomic with zeros
	S zeroes = {0, 0, 0, 0, 0};
	shared.store(zeroes, std::memory_order_relaxed);
	//atomic_store_explicit(&shared, {0, 0, 0, 0, 0}, std::memory_order_relaxed);

	pthread_t threads[NB_THREADS];
	unsigned long thread_iterations[NB_THREADS];
	for (int i = 0; i < NB_THREADS; ++i)
		pthread_create(&threads[i], NULL, worker, NULL);

	// Run for a fixed duration
	std::this_thread::sleep_for(std::chrono::seconds(RUN_DURATION_SECONDS));
	atomic_store_explicit(&done, 1, std::memory_order_relaxed);

	for (int i = 0; i < NB_THREADS; ++i) {
        void* return_value;
		pthread_join(threads[i], &return_value);
		thread_iterations[i] = (unsigned long) return_value;
	}

	std::cout << "total_iterations=" << iterations_total.load();
	std::cout << ";duration=" << RUN_DURATION_SECONDS;
	std::cout << ";nb_threads=" << NB_THREADS;

	// print per thread iterations
	for (size_t k = 0u; k < NB_THREADS; ++k) {
		std::cout << ";thread_" << k << "=" << thread_iterations[k];
	}

	std::cout << "\n";
    pthread_mutex_destroy(&lock);

    return 0;
}
