#include <vsync/spinlock/ticketlock.h>
#include <tilt.h>

typedef struct tilt_mutex {
    ticketlock_t lock;
} tilt_mutex_t;

static void tilt_mutex_init(tilt_mutex_t *m)
{
    ticketlock_init(&m->lock);
}

static void tilt_mutex_destroy(tilt_mutex_t *m)
{
}

static void tilt_mutex_lock(tilt_mutex_t *m)
{
    ticketlock_acquire(&m->lock);
}

static void
tilt_mutex_unlock(tilt_mutex_t *m)
{
    ticketlock_release(&m->lock);
}

static bool
tilt_mutex_trylock(tilt_mutex_t *m)
{
    return ticketlock_tryacquire(&m->lock);
}
