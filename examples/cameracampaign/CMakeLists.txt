cmake_minimum_required(VERSION 3.10)
project(CameraProcessingExample C CXX)  # Enable both C and CXX

# Set the C and C++ Standard
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 11)

# Find packages
find_package(Threads REQUIRED)
find_package(realsense2 REQUIRED)
find_package(OpenCV REQUIRED)

# Add new C++ executables
add_executable(CameraProcessing src/camera_processing.cpp)

# Include directories for the C++ executable
target_include_directories(CameraProcessing PRIVATE ${OpenCV_INCLUDE_DIRS})

# Link libraries for the new C++ executable
target_link_libraries(CameraProcessing PRIVATE
    ${realsense2_LIBRARY}
    ${OpenCV_LIBS}
    Threads::Threads)

