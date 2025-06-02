# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.10)
project(
    reciplock
    LANGUAGES C
    VERSION 2.1.0
)

include_directories(include)
add_library(reciplock INTERFACE)
target_include_directories(reciplock INTERFACE include)
