#include <stdio.h>
#include <pthread.h>

int main() {
    pthread_mutex_t lock;

    if (pthread_mutex_init(&lock, NULL) != 0) {
        printf("Mutex initialization failed\n");
        return 1;
    }

    printf("Locking mutex...\n");
    pthread_mutex_lock(&lock);
    printf("Mutex locked\n");

    printf("Unlocking mutex...\n");
    pthread_mutex_unlock(&lock);
    printf("Mutex unlocked\n");

    pthread_mutex_destroy(&lock);

    return 0;
}
