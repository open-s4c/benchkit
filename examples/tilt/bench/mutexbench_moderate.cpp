#include <stdio.h>
#include <pthread.h>
#include <string.h>
#include <atomic>
#include <random>
#include <chrono>
#include <iostream>
#include <vector>
#include <thread>

#define THREAD_COUNT 8
#define BENCH_DURATION_SEC 10

#define IMPLICIT_INIT

pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

std::mt19937 prng_global{42}; // shared global PRNG
std::atomic<bool> done{false};
std::atomic<uint64_t> iterations_total{0};

void* worker(void* arg) {
	uint64_t iterations_local = 0;
	std::mt19937 prng_local{42}; // local PRNG
	while (!atomic_load_explicit(&done, std::memory_order_relaxed)) {
		pthread_mutex_lock(&lock);
		// Critical section
		prng_global(); // one step of PRNG in critical section

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

	pthread_t threads[THREAD_COUNT];
	for (int i = 0; i < THREAD_COUNT; ++i)
		pthread_create(&threads[i], NULL, worker, NULL);

	//sleep(BENCH_DURATION_SEC);
	std::this_thread::sleep_for(std::chrono::seconds(BENCH_DURATION_SEC));
	atomic_store_explicit(&done, 1, std::memory_order_relaxed);


	for (int i = 0; i < THREAD_COUNT; ++i)
		pthread_join(threads[i], NULL);

	std::cout << "Total iterations: " << iterations_total.load() << "\n";
    pthread_mutex_destroy(&lock);

    return 0;
}
