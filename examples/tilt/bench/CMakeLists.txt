cmake_minimum_required(VERSION 3.10)
project(PthreadMutexExample)

set(CMAKE_C_STANDARD 99)

add_executable(mutex mutex.c)

find_package(Threads REQUIRED)
target_link_libraries(mutex Threads::Threads)
