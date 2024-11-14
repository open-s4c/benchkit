# add_executable(mainmerde main.cpp)
# add_executable(testmerde test.cpp)
# add_sycl_to_target(TARGET mainmerde SOURCES main.cpp)
# add_sycl_to_target(TARGET testmerde SOURCES test.cpp)

function(add_benchmark filename)
    add_executable("${filename}" "${filename}.cpp")
    add_sycl_to_target(TARGET "${filename}" SOURCES "${filename}.cpp")
endfunction()

add_benchmark(add)
add_benchmark(matmul)

set(WGROUP_SIZE 16 CACHE STRING 16)
target_compile_definitions(add PRIVATE -DWGROUP_SIZE=${WGROUP_SIZE})


install(TARGETS add
        RUNTIME DESTINATION share/hipSYCL/examples/)