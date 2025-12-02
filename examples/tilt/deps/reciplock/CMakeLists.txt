# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

cmake_minimum_required(VERSION 3.10)
project(
    reciplock_headers
    LANGUAGES C
    VERSION 2.1.0
)

include_directories(include)
add_library(reciplock_headers INTERFACE)
target_include_directories(reciplock_headers INTERFACE include)
