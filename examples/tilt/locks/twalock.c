#include <vsync/spinlock/twalock.h>
#include <tilt.h>

TWALOCK_ARRAY_DECL;
twalock_t g_lock = TWALOCK_INIT();

typedef struct tilt_mutex {
    twalock_t lock;
} tilt_mutex_t;

static void tilt_mutex_init(tilt_mutex_t *m)
{
    twalock_init(&m->lock);
}

static void tilt_mutex_destroy(tilt_mutex_t *m)
{
}

static void tilt_mutex_lock(tilt_mutex_t *m)
{
    twalock_acquire(&m->lock);
}

static void
tilt_mutex_unlock(tilt_mutex_t *m)
{
    twalock_release(&m->lock);
}

static bool
tilt_mutex_trylock(tilt_mutex_t *m)
{
    return twalock_tryacquire(&m->lock);
}
