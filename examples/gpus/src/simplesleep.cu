#include <iostream>
#include <chrono>
#include <thread>
#include <cuda_runtime.h>

// Simple kernel: increments each element
__global__ void simpleKernel(int *data, int size) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        data[idx] += 1;
    }
}

// Simple kernel with artificial delay
__global__ void delayedKernel1(int *data, int size, int delay_iters = 1000000) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        int tmp = data[idx];
        // Artificial work: spin in a loop
        for (int i = 0; i < delay_iters; ++i) {
            tmp += i % 7; // just some computation
        }
        data[idx] = tmp;
    }
}

// Simple kernel with artificial delay
__global__ void delayedKernel2(int *data, int size, int delay_iters = 1000000 / 2) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        int tmp = data[idx];
        // Artificial work: spin in a loop
        for (int i = 0; i < delay_iters; ++i) {
            tmp += i % 7; // just some computation
        }
        data[idx] = tmp;
    }
}

// Helper to print timestamp since start
auto get_relative_time(std::chrono::steady_clock::time_point start) {
    auto now = std::chrono::steady_clock::now();
    auto us = std::chrono::duration_cast<std::chrono::microseconds>(now - start).count();
    return us / 1000.0; // convert to milliseconds
}

int main() {
    const int size = 1 << 20; // 1M elements
    const int bytes = size * sizeof(int);

    int *h_data = new int[size];
    for (int i = 0; i < size; i++) {
        h_data[i] = i;
    }

    int *d_data;
    cudaMalloc(&d_data, bytes);
    cudaMemcpy(d_data, h_data, bytes, cudaMemcpyHostToDevice);

    int threads = 256;
    int blocks = (size + threads - 1) / threads;

    // Start the timeline
    auto start_time = std::chrono::steady_clock::now();

    std::cout << "[" << get_relative_time(start_time) << " ms] Launching kernel 1..." << std::endl;
    delayedKernel1<<<blocks, threads>>>(d_data, size);
    cudaDeviceSynchronize();

    std::cout << "[" << get_relative_time(start_time) << " ms] Sleeping..." << std::endl;
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    std::cout << "[" << get_relative_time(start_time) << " ms] Launching kernel 2..." << std::endl;
    delayedKernel2<<<blocks, threads>>>(d_data, size);
    cudaDeviceSynchronize();

    cudaMemcpy(h_data, d_data, bytes, cudaMemcpyDeviceToHost);

    std::cout << "[" << get_relative_time(start_time) << " ms] Checking results..." << std::endl;
    std::cout << "Sample results: ";
    for (int i = 0; i < 5; i++) {
        std::cout << h_data[i] << " ";
    }
    std::cout << "..." << std::endl;

    cudaFree(d_data);
    delete[] h_data;

    std::cout << "[" << get_relative_time(start_time) << " ms] Done!" << std::endl;

    return 0;
}
