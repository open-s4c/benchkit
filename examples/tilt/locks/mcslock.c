// Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
// SPDX-License-Identifier: MIT

#include <vsync/spinlock/mcslock.h>
#include <tilt.h>

static __thread mcs_node_t context;

typedef struct tilt_mutex {
    mcslock_t lock;
} tilt_mutex_t;

static void
tilt_mutex_init(tilt_mutex_t *m)
{
    mcslock_init(&m->lock);
}

static void
tilt_mutex_destroy(tilt_mutex_t *m)
{
}

static void
tilt_mutex_lock(tilt_mutex_t *m)
{
    mcslock_acquire(&m->lock, &context);
}

static void
tilt_mutex_unlock(tilt_mutex_t *m)
{
    mcslock_release(&m->lock, &context);
}

static bool
tilt_mutex_trylock(tilt_mutex_t *m)
{
}

