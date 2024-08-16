cmake_minimum_required(VERSION 3.10)

project(caslock C)

add_subdirectory(${CMAKE_SOURCE_DIR}/../deps/libvsync/ build_libvsync)

include_directories(include ${CMAKE_SOURCE_DIR}/../deps/tilt/include/)

add_library(taslock SHARED taslock.c)
add_library(caslock SHARED caslock.c)
add_library(vcaslock-lse SHARED vcaslock.c)
add_library(vcaslock-nolse SHARED vcaslock.c)

target_link_libraries(vcaslock-lse vsync)
target_link_libraries(vcaslock-nolse vsync)

target_compile_definitions(vcaslock-nolse PRIVATE VATOMIC_DISABLE_ARM64_LSE)
