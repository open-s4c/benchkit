#include <reciplock.h>
#include <tilt.h>

typedef struct tilt_mutex {
    reciplock_t lock;
} tilt_mutex_t;

static void tilt_mutex_init(tilt_mutex_t *m)
{
    reciplock_init(&m->lock);
}

static void tilt_mutex_destroy(tilt_mutex_t *m)
{

}

static void tilt_mutex_lock(tilt_mutex_t *m)
{
	reciplock_acquire(&m->lock);
}

static void
tilt_mutex_unlock(tilt_mutex_t *m)
{
	reciplock_release(&m->lock);
}

static bool
tilt_mutex_trylock(tilt_mutex_t *m)
{
}
