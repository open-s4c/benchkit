# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.10)
project(PthreadMutex)
# project(PthreadMutex LANGUAGES C CXX)

# Build options
set(NB_THREADS 4 CACHE STRING "Number of threads increasing the counter")
set(RUN_DURATION_SECONDS 10 CACHE STRING "Time during which the threads will increase the counter")

set(CMAKE_C_STANDARD 99)
# set(CMAKE_CXX_STANDARD 11)

configure_file(${CMAKE_SOURCE_DIR}/include/config.h.in ${CMAKE_BINARY_DIR}/include/config.h)

include_directories(${CMAKE_CURRENT_BINARY_DIR}/include)

add_executable(test_mutex test_mutex.c)
add_executable(bench_mutex bench_mutex.cpp)
add_executable(bench_mutex_moderate bench_mutex_moderate.cpp)
# add_executable(bench_atomic bench_atomic.cpp)

find_package(Threads REQUIRED)
target_link_libraries(test_mutex Threads::Threads)
target_link_libraries(bench_mutex Threads::Threads)
target_link_libraries(bench_mutex_moderate Threads::Threads)
# target_link_libraries(bench_atomic Threads::Threads)
