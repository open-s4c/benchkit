cmake_minimum_required(VERSION 3.10)

project(caslock C)

add_subdirectory(${CMAKE_SOURCE_DIR}/../deps/libvsync/ build_libvsync)

include_directories(include ${CMAKE_SOURCE_DIR}/../deps/tilt/include/)

add_library(caslock SHARED caslock.c)
add_library(vcaslock SHARED vcaslock.c)

target_link_libraries(vcaslock vsync)
