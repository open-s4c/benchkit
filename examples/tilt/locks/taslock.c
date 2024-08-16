#include <stdatomic.h>
#include <tilt.h>

typedef struct tilt_mutex {
    atomic_int lock;
} tilt_mutex_t;

static void tilt_mutex_init(tilt_mutex_t *m)
{
    m->lock = 0;
}

static void tilt_mutex_destroy(tilt_mutex_t *m)
{
    m->lock = 0;
}

static void tilt_mutex_lock(tilt_mutex_t *m)
{
    while (atomic_exchange(&m->lock, 1));
}

static void
tilt_mutex_unlock(tilt_mutex_t *m)
{
    m->lock = 0;
}

static bool
tilt_mutex_trylock(tilt_mutex_t *m)
{
    return 0 == atomic_exchange(&m->lock, 1);
}
