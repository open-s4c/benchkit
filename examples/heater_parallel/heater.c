#define _GNU_SOURCE
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include <sched.h>
#include <stdatomic.h>
#include <sys/time.h>
#include <numa.h>

#define DEFAULT_DURATION_S 0.05

atomic_int* counter_ptr;

static void assign_thread_to_core(pthread_t thread, const size_t core) {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core, &cpuset);
    pthread_setaffinity_np(thread, sizeof(cpu_set_t), &cpuset);
}

static long get_current_time_ms(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

struct thread_params {
    size_t core;
    size_t thread_id;
    int duration_ms;
};

static void *increment_counter(void *arg) {
    const struct thread_params *p = (const struct thread_params*) arg;

    assign_thread_to_core(pthread_self(), p->core);
    const int is_even_thread = (p->thread_id == 0);

    const long end_time = get_current_time_ms() + p->duration_ms;
    while (get_current_time_ms() < end_time) {
        int expected = atomic_load(counter_ptr);
        if ((expected % 2 == 0) == is_even_thread) {
            atomic_compare_exchange_strong(counter_ptr, &expected, expected + 1);
        }
    }

    pthread_exit(NULL);
}

int main(int argc, char *argv[]) {
    pthread_t threads[2];
    struct thread_params params[2];

    const long num_cores = sysconf(_SC_NPROCESSORS_ONLN);

    if (argc < 3 || argc > 4) {
        fprintf(stderr,
            "Usage: %s CORE1 CORE2 [DURATION_S]\n"
            "  CORE1/CORE2 in [0, %ld)\n"
            "  DURATION_S default: %.2f\n",
            argv[0], num_cores, DEFAULT_DURATION_S);
        return EXIT_FAILURE;
    }

    char *end = NULL;
    long c1 = strtol(argv[1], &end, 10);
    if (*end || c1 < 0 || c1 >= num_cores) { fprintf(stderr, "Invalid CORE1\n"); return EXIT_FAILURE; }
    long c2 = strtol(argv[2], &end, 10);
    if (*end || c2 < 0 || c2 >= num_cores) { fprintf(stderr, "Invalid CORE2\n"); return EXIT_FAILURE; }

    float duration_s = (argc > 3) ? atof(argv[3]) : DEFAULT_DURATION_S;
    int duration_ms = (int)(duration_s * 1000);

    printf("Running core pair [%ld, %ld] for %.2f s (%d ms)…\n", c1, c2, duration_s, duration_ms);

    params[0] = (struct thread_params){ .core = (size_t)c1, .thread_id = 0, .duration_ms = duration_ms };
    params[1] = (struct thread_params){ .core = (size_t)c2, .thread_id = 1, .duration_ms = duration_ms };

    assign_thread_to_core(pthread_self(), c1);
    counter_ptr = numa_alloc_local(sizeof(atomic_int));
    atomic_store(counter_ptr, 0);

    pthread_create(&threads[0], NULL, increment_counter, &params[0]);
    pthread_create(&threads[1], NULL, increment_counter, &params[1]);

    pthread_join(threads[0], NULL);
    pthread_join(threads[1], NULL);

    int counter = atomic_load(counter_ptr);
    numa_free(counter_ptr, sizeof(atomic_int));

    printf("Core combination [%ld, %ld]: Counter = %d\n", c1, c2, counter);
    return 0;
}
