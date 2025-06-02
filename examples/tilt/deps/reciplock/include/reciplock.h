// Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
// SPDX-License-Identifier: MIT

#ifndef RECIP_RECIPLOCK_H
#define RECIP_RECIPLOCK_H
/*******************************************************************************
 * @file  reciplock.h
 * @brief one sentence that describes the algorithm.
 *
 * @ingroup lock_free // if your algo belongs to certain groups you
 *                    // can list them here separated with spaces
 *
 *
 * // add detailed information about the algorithm
 * // operating conditions etc.
 *
 *
 * @example
 * @include eg_reciplock.c
 * *
 * @cite
 * David Dice, Alex Kogan - [Reciprocating Locks. arXiv:2501.02380]
 ******************************************************************************/

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdatomic.h>
#include <inttypes.h>
#include <assert.h>

#define TLS_IMPLEMENTATION 1

// a thread knows only the identity of its immediate neighbor in the arrival segment
typedef struct reciplock_node_s {
	_Atomic(struct reciplock_node_s *) next; // next node in waiting
} reciplock_node_t;

/** Reciprocating lock data structure. */
typedef struct reciplock_s {
	_Atomic(reciplock_node_t *) tail; // tail of the arrival segment
} reciplock_t;

// Spinner, if not nullptr then we can enter critical section
static __thread reciplock_node_t tls_wait_node; // thread-specific waiting element

#if TLS_IMPLEMENTATION
static __thread reciplock_node_t *tls_successor;
static __thread reciplock_node_t *tls_end_of_segment;
#endif

// encoding of the "simple-locked" state, lock is active but nothing in entry segment
static reciplock_node_t * const LOCKED_EMPTY = (reciplock_node_t *)(uintptr_t) 1;

/** Initializer of `reciplock_t`. */
#define RECIPLOCK_INIT() 				\
{                        				\
	.tail = ATOMIC_VAR_INIT(NULL) 		\
}

/**
 * Initializes the reciprocating lock.
 *
 * @param lock address of reciplock_t object.
 *
 * @note alternatively use `RECIPLOCK_INIT`.
 */
static inline void
reciplock_init(reciplock_t *lock)
{
	atomic_store_explicit( &lock->tail, NULL, memory_order_release );
}

// segment_end and succ reflect context to be passed from Acquire to corresponding Release
// Could also pass the context via fields in the lock body or into TLS.

/**
 * Acquires the reciprocating lock.
 *
 * @param lock address of reciplock_t object.
 * @param _segment_end address of reciplock_node_t object, associated with the calling
 * thread/core.
 * @return Pointer to successor node if one exists; NULL otherwise.
 *
 * Each thread uses its own tls_wait_node for participation.
 * @remarks segment_end and successor node are used to pass context from Acquire to Release.
 * Could also pass the context via fields in the lock body or into TLS.
 */
static inline reciplock_node_t *
#if TLS_IMPLEMENTATION
reciplock_acquire( reciplock_t *lock )
#else
reciplock_acquire( reciplock_t *lock, reciplock_node_t **_segment_end )
#endif
{
	// initializes its thread-specific waiting element in anticipation of potential contention
	atomic_store_explicit( &tls_wait_node.next, NULL, memory_order_release );

	reciplock_node_t *succ = NULL;
	reciplock_node_t *segment_end = &tls_wait_node; // currently nullptr

	// swaps the address of wait_element into lock's arrival word;
	reciplock_node_t *const tail_prev = atomic_exchange( &lock->tail, &tls_wait_node );
	assert( tail_prev != &tls_wait_node );

	// Lock is held
	if ( tail_prev != NULL ) {
		// coerce LOCKED_EMPTY to null
		// succ will be our successor when we subsequently release
		succ = (reciplock_node_t *)(((uintptr_t) tail_prev) & ~1);
		assert(succ != &tls_wait_node);

		// Spin until our predecessor grants us access.
		for ( ;; ) {
			segment_end = atomic_load_explicit( &tls_wait_node.next, memory_order_acquire );
			if ( segment_end != NULL ) break;
			//Pause();
		}
		assert( segment_end != &tls_wait_node );

		// Detect logical end-of-segment terminus address
		if ( succ == segment_end ) {
			succ = NULL;         // quash
			segment_end = LOCKED_EMPTY;
		}
	}
#if TLS_IMPLEMENTATION
	tls_successor = succ;
	tls_end_of_segment = segment_end;
#else
	*_segment_end = segment_end;
#endif
	return succ;
}

#if TLS_IMPLEMENTATION
/**
 * Releases the reciprocating lock.
 *
 * @param lock address of reciplock_t object.
 */
static inline void
reciplock_release( reciplock_t *lock ) {
	assert( tls_end_of_segment != NULL );
	assert( atomic_load_explicit(&lock->tail, memory_order_acquire) != NULL );

	if ( tls_successor != NULL ) {
		assert( atomic_load(&tls_successor->next) == NULL );

		// Notify successor that it may proceed.
		atomic_store_explicit( &tls_successor->next, tls_end_of_segment, memory_order_release );
		return;
	}

	assert( tls_end_of_segment == LOCKED_EMPTY || tls_end_of_segment == &tls_wait_node );
#if 0
	reciplock_node_t * v = tls_end_of_segment;

    // empty entry segment
	if ( atomic_compare_exchange_strong_explicit( &lock->tail, &v, NULL, __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST ) ) {
		// uncontended fast-path return
		return;
	}
#else
	// Fast path: if the tail is empty, we can just set it to NULL
	if ( atomic_load_explicit( &lock->tail, memory_order_acquire ) == tls_end_of_segment ) {
		reciplock_node_t *v = tls_end_of_segment;
		if ( atomic_compare_exchange_strong_explicit( &lock->tail, &v, NULL, memory_order_seq_cst, memory_order_seq_cst ) ) {
			// uncontended fast-path return
			return;
		}
	}
#endif

	// Slow path: tail is not empty, we need to detach the arrival segment
	reciplock_node_t *w = atomic_exchange( &lock->tail, LOCKED_EMPTY ); //  detach arrival segment
	assert( w != NULL );
	assert( w != LOCKED_EMPTY );
	assert( w != &tls_wait_node );
	assert( atomic_load_explicit( &w->next, memory_order_acquire ) == NULL );

	// Let the new arrival know the segment's boundary
	atomic_store_explicit( &w->next, tls_end_of_segment, memory_order_release ); // pass ownership; pass address of wait_element as end of segment marker
}
#else
/**
 * Releases the reciprocating lock.
 *
 * @param lock address of reciplock_t object.
 * @param end_of_segment address of reciplock_node_t object, associated with the calling
 * thread/core.
 * @param succ address of successor node (if one exists), to which control is handed off.
 * @remarks segment_end and successor node are used to pass context from Acquire to Release.
 * Could also pass the context via fields in the lock body or into TLS.
 */
static inline void
reciplock_release( reciplock_t *lock, reciplock_node_t *end_of_segment, reciplock_node_t *succ ) {
	assert( end_of_segment != NULL );
	assert( atomic_load_explicit(&lock->tail, memory_order_acquire) != NULL );

	if ( succ != NULL ) {
		assert( atomic_load(&succ->next) == NULL );

		// Notify successor that it may proceed.
		atomic_store_explicit( &succ->next, end_of_segment, memory_order_release );
		return;
	}

	assert( end_of_segment == LOCKED_EMPTY || end_of_segment == &tls_wait_node );
#if 0
	reciplock_node_t * v = end_of_segment;

    // empty entry segment
	if ( atomic_compare_exchange_strong_explicit( &lock->tail, &v, NULL, __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST ) ) {
		// uncontended fast-path return
		return;
	}
#else
	// Fast path: if the tail is empty, we can just set it to NULL
	if ( atomic_load_explicit( &lock->tail, memory_order_acquire ) == end_of_segment ) {
		reciplock_node_t *v = end_of_segment;
		if ( atomic_compare_exchange_strong_explicit( &lock->tail, &v, NULL, memory_order_seq_cst, memory_order_seq_cst ) ) {
			// uncontended fast-path return
			return;
		}
	}
#endif

	// Slow path: tail is not empty, we need to detach the arrival segment
	reciplock_node_t *w = atomic_exchange( &lock->tail, LOCKED_EMPTY ); //  detach arrival segment
	assert( w != NULL );
	assert( w != LOCKED_EMPTY );
	assert( w != &tls_wait_node );
	assert( atomic_load_explicit( &w->next, memory_order_acquire ) == NULL );

	// Let the new arrival know the segment's boundary
	atomic_store_explicit( &w->next, end_of_segment, memory_order_release ); // pass ownership; pass address of wait_element as end of segment marker
}
#endif

//void __attribute__((noinline)) ctor() {
//	atomic_store_explicit( &lock.arrivals, NULL, memory_order_release );
//} // ctor
//
//void __attribute__((noinline)) dtor() {
//} // dtor
#endif //RECIP_RECIPLOCK_H
