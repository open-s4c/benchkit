#define _GNU_SOURCE
#include <stdio.h>
#include <pthread.h>
#include <unistd.h>
#include <sched.h>
#include <stdlib.h>
#include <stdatomic.h>

#define NUM_THREADS 1 // Number of worker threads
#define WORK_DURATION 5 // Seconds to perform busy work
#define MIGRATION_INTERVAL 1 // Interval (in seconds) to change CPU affinity

atomic_int stop = 0;

void *busy_work(void *arg) {
    int thread_id = *(int *)arg;
    while (!atomic_load(&stop)) {
        // Perform busy work
        for (volatile int i = 0; i < 1000000; ++i);
    }
    printf("Thread %d exiting.\n", thread_id);
    return NULL;
}

void pin_thread_to_cpu(pthread_t thread, int cpu) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(cpu, &cpuset);

    if (pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset) != 0) {
        perror("Error setting thread affinity");
    } else {
        printf("Thread pinned to CPU %d\n", cpu);
    }
}

void pin_main_thread_to_cpu(int cpu) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(cpu, &cpuset);

    if (sched_setaffinity(0, sizeof(cpu_set_t), &cpuset) != 0) {
        perror("Error pinning main thread to CPU");
    } else {
        printf("Main thread pinned to CPU %d\n", cpu);
    }
}

int main() {
    // Pin the main thread to CPU 0
    pin_main_thread_to_cpu(0);

    pthread_t threads[NUM_THREADS];
    int thread_ids[NUM_THREADS];

    // Create worker threads
    for (int i = 0; i < NUM_THREADS; i++) {
        thread_ids[i] = i;
        if (pthread_create(&threads[i], NULL, busy_work, &thread_ids[i]) != 0) {
            perror("Failed to create thread");
            exit(EXIT_FAILURE);
        }
    }

    // Main thread: periodically change thread affinity for worker threads
    int cpu = 0;
    for (int t = 0; t < WORK_DURATION / MIGRATION_INTERVAL; t++) {
        sleep(MIGRATION_INTERVAL);

        cpu = (cpu + 1) % sysconf(_SC_NPROCESSORS_ONLN); // Rotate CPUs
        for (int i = 0; i < NUM_THREADS; i++) {
            pin_thread_to_cpu(threads[i], cpu);
        }
    }

    // Signal threads to stop and join them
    atomic_store(&stop, 1);
    for (int i = 0; i < NUM_THREADS; i++) {
        pthread_join(threads[i], NULL);
    }

    printf("All threads finished.\n");
    return 0;
}
