#include <vsync/spinlock/hemlock.h>
#include <tilt.h>

static __thread hem_node_t context;

typedef struct tilt_mutex {
    hemlock_t lock;
} tilt_mutex_t;

static void
tilt_mutex_init(tilt_mutex_t *m)
{
    hemlock_init(&m->lock);
}

static void
tilt_mutex_destroy(tilt_mutex_t *m)
{
}

static void
tilt_mutex_lock(tilt_mutex_t *m)
{
    hemlock_acquire(&m->lock, &context);
}

static void
tilt_mutex_unlock(tilt_mutex_t *m)
{
    hemlock_release(&m->lock, &context);
}

static bool
tilt_mutex_trylock(tilt_mutex_t *m)
{
	return hemlock_tryacquire(&m->lock, &context);
}

