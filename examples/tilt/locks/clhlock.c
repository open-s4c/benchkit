#include <vsync/spinlock/clhlock.h>
#include <tilt.h>

static __thread clh_node_t context;

typedef struct tilt_mutex {
    clhlock_t lock;
} tilt_mutex_t;

static void
tilt_mutex_init(tilt_mutex_t *m)
{
    clhlock_init(&m->lock);
}

static void
tilt_mutex_destroy(tilt_mutex_t *m)
{
}

static void
tilt_mutex_lock(tilt_mutex_t *m)
{
    clhlock_acquire(&m->lock, &context);
}

static void
tilt_mutex_unlock(tilt_mutex_t *m)
{
    clhlock_release(&m->lock, &context);
}

static bool
tilt_mutex_trylock(tilt_mutex_t *m)
{
}

