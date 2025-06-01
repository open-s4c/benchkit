# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.10)
project(PthreadMutexExample)

# Build options
set(NB_THREADS 4 CACHE STRING "Number of threads increasing the counter")
set(RUN_DURATION_SECONDS 10 CACHE STRING "Time during which the threads will increase the counter")

set(CMAKE_C_STANDARD 99)

configure_file(${CMAKE_SOURCE_DIR}/include/config.h.in ${CMAKE_BINARY_DIR}/include/config.h)

include_directories(${CMAKE_CURRENT_BINARY_DIR}/include)

add_executable(mutex_test mutex_test.c)
# add_executable(atomic_bench atomic_bench.cpp)
add_executable(mutex_bench mutex_bench.cpp)

find_package(Threads REQUIRED)
target_link_libraries(mutex_test Threads::Threads)
target_link_libraries(mutex_bench Threads::Threads)
# target_link_libraries(atomic_bench Threads::Threads)
