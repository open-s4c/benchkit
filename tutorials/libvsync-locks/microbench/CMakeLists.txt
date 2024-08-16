# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.22)
project(libvsync-locks C)

# Build options
set(LOCK cas CACHE STRING "Lock implementation to protect the counter")
set(NB_THREADS 4 CACHE STRING "Number of threads increasing the counter")
set(RUN_DURATION_SECONDS 2 CACHE STRING "Time during which the threads will increase the counter")

# To change the compiler, set the following:
# set(CMAKE_C_COMPILER /usr/bin/gcc-7)
# To generate LSE instructions on Armv8, set the following:
# target_compile_options(${PROJECT_NAME} PUBLIC "-march=armv8-a+lse")

set(LIBVSYNC_DIR "${CMAKE_SOURCE_DIR}/deps/libvsync")
add_subdirectory(${LIBVSYNC_DIR})

configure_file(${CMAKE_SOURCE_DIR}/include/config.h.in ${CMAKE_BINARY_DIR}/include/config.h)

add_executable(${PROJECT_NAME} src/${PROJECT_NAME}.c)
target_link_libraries(${PROJECT_NAME} vsync pthread)
target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_BINARY_DIR}/include)
