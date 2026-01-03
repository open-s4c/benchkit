# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.10)

project(tiltlock C)

add_subdirectory(${CMAKE_SOURCE_DIR}/../deps/libvsync/ build_libvsync)

add_subdirectory(${CMAKE_SOURCE_DIR}/../deps/reciplock/ build_reciplock)

include_directories(include ${CMAKE_SOURCE_DIR}/../deps/tilt/include/)

add_library(taslock SHARED taslock.c)
add_library(caslock SHARED caslock.c)
add_library(vcaslock-lse SHARED vcaslock.c)
add_library(vcaslock-nolse SHARED vcaslock.c)
add_library(clhlock SHARED clhlock.c)
add_library(hemlock SHARED hemlock.c)
add_library(mcslock SHARED mcslock.c)
add_library(ticketlock SHARED ticketlock.c)
add_library(twalock SHARED twalock.c)
add_library(reciplock SHARED reciplock.c)

target_link_libraries(vcaslock-lse vsync)
target_link_libraries(vcaslock-nolse vsync)
target_link_libraries(clhlock vsync)
target_link_libraries(hemlock vsync)
target_link_libraries(mcslock vsync)
target_link_libraries(ticketlock vsync)
target_link_libraries(twalock vsync)
target_link_libraries(reciplock reciplock_headers)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64" OR CMAKE_SYSTEM_PROCESSOR MATCHES "armv8")
    target_compile_definitions(vcaslock-nolse PRIVATE VATOMIC_DISABLE_ARM64_LSE)
    target_compile_options(vcaslock-lse PRIVATE -march=armv8-a+lse)
endif()
