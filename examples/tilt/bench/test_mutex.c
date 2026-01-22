// Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
// SPDX-License-Identifier: MIT

#include <stdio.h>
#include <pthread.h>
#include <string.h>

#define IMPLICIT_INIT

int main() {
    pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

    #if !defined(IMPLICIT_INIT)
    if (pthread_mutex_init(&lock, NULL) != 0) {
        printf("Mutex initialization failed\n");
        return 1;
    }
    #endif /* EXPLICIT_INIT */

    printf("Locking mutex...\n");
    pthread_mutex_lock(&lock);
    printf("Mutex locked\n");

    printf("Unlocking mutex...\n");
    pthread_mutex_unlock(&lock);
    printf("Mutex unlocked\n");

    pthread_mutex_destroy(&lock);

    return 0;
}
