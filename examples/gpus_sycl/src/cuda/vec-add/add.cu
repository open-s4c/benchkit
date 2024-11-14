// https://developer.nvidia.com/blog/even-easier-introduction-cuda/

#include <iostream>
#include <assert.h>
#include <chrono>
#include <math.h>

#ifndef BLOCK_SIZE
#define BLOCK_SIZE 1024 // max
#endif

__global__
void add(int n, float *x, float *y) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
        y[i] = x[i] + y[i];
}

int main(void) {
    int n = 1<<25;
    float *x, *y;
    cudaMallocManaged(&x, n*sizeof(float));
    cudaMallocManaged(&y, n*sizeof(float));

    for (int i=0; i < n; i++) {
        x[i] = 1.0f;
        y[i] = 1.0f;
    }

    int numBlocks = (n + BLOCK_SIZE - 1) / BLOCK_SIZE;
    printf("%d %d\n", BLOCK_SIZE, numBlocks);
    // test events
    cudaEvent_t e_start, e_stop;
    cudaEventCreate(&e_start);
    cudaEventCreate(&e_stop);
    
    auto start = std::chrono::high_resolution_clock::now();
    cudaEventRecord(e_start, 0);
    add<<<numBlocks, BLOCK_SIZE>>>(n, x, y);
    cudaEventRecord(e_stop, 0);
    cudaEventSynchronize(e_stop);
    // cudaDeviceSynchronize();
    auto stop = std::chrono::high_resolution_clock::now();
    cudaError_t code = cudaPeekAtLastError();
    if (code != cudaSuccess) {
        fprintf(stderr,"GPUassert: %s\n", cudaGetErrorString(code));
    }

    std::chrono::duration<double> duration = stop - start;
    std::cout << "duration: " << duration.count()*1000.0f << std::endl;
    float kernel_time = 0;
    cudaEventElapsedTime(&kernel_time, e_start, e_stop);
    std::cout << "kernel_time: " << kernel_time << std::endl;

    cudaFree(x);
    cudaFree(y);
}