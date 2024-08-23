cmake_minimum_required(VERSION 3.10)

project(tiltlock C)

add_subdirectory(${CMAKE_SOURCE_DIR}/../deps/libvsync/ build_libvsync)

include_directories(include ${CMAKE_SOURCE_DIR}/../deps/tilt/include/)

add_library(taslock SHARED taslock.c)
add_library(caslock SHARED caslock.c)
add_library(vcaslock-lse SHARED vcaslock.c)
add_library(vcaslock-nolse SHARED vcaslock.c)

target_link_libraries(vcaslock-lse vsync)
target_link_libraries(vcaslock-nolse vsync)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64" OR CMAKE_SYSTEM_PROCESSOR MATCHES "armv8")
    target_compile_definitions(vcaslock-nolse PRIVATE VATOMIC_DISABLE_ARM64_LSE)
    target_compile_options(vcaslock-lse PRIVATE -march=armv8-a+lse)
endif()
