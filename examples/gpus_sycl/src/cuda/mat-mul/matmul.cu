
#include <iostream>
#include <chrono>
#include <assert.h>
#include <math.h>
#include <fcntl.h>
#include <unistd.h>

#ifndef BLOCK_SIZE
#define BLOCK_SIZE 32 // max 1024 threads per block
#endif

__global__
void matmul(int n, int *a, int *b, int *c) {
    int y = blockIdx.y * blockDim.y + threadIdx.y;
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int tmp = 0;
    for (int i=0; i<n; i++) {
        tmp += a[n*y+i] * b[n*i+x];
    }
    c[y*n+x] = tmp;
}

void verify(int n, int *a, int *b, int *c) {
    for (int y=0; y<n; y++) {
        for (int x=0; x<n; x++) {
            int tmp = 0;
            for (int i=0; i<n; i++) {
                tmp += a[n*y+i] * b[n*i+x];
            }
            assert(tmp == c[y*n+x]);
        }
    }
}

int main(void) {
    int n = 1024;
    int size = n*n;

    // host memory
    int *h_a = (int*)malloc(size*sizeof(int));
    int *h_b = (int*)malloc(size*sizeof(int));
    int *h_c = (int*)calloc(size, sizeof(int));

    // device memory
    int *d_a, *d_b, *d_c;
    cudaMalloc(&d_a, size*sizeof(int));
    cudaMalloc(&d_b, size*sizeof(int));
    cudaMalloc(&d_c, size*sizeof(int));
    float test = (n + BLOCK_SIZE - 1) / BLOCK_SIZE;
    int numBlocks = (n + BLOCK_SIZE - 1) / BLOCK_SIZE;

    dim3 dimGrid(numBlocks, numBlocks, 1);
    dim3 dimBlock(BLOCK_SIZE, BLOCK_SIZE, 1);
    printf("%d %d %f\n", BLOCK_SIZE, numBlocks, test);

    for (int i=0; i<size; i++) {
        h_a[i] = 1;
        h_b[i] = 2;
    }
    // copy over
    cudaMemcpy(d_a, h_a, size*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, size*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_c, h_c, size*sizeof(int), cudaMemcpyHostToDevice);

    // test events
    cudaEvent_t e_start, e_stop;
    cudaEventCreate(&e_start);
    cudaEventCreate(&e_stop);

    auto start = std::chrono::high_resolution_clock::now();
    cudaEventRecord(e_start);
    matmul<<<dimGrid, dimBlock>>>(n, d_a, d_b, d_c);
    cudaEventRecord(e_stop);
    // cudaDeviceSynchronize();
    cudaEventSynchronize(e_stop);

    cudaError_t code = cudaPeekAtLastError();
    if (code != cudaSuccess) {
        fprintf(stderr,"GPUassert: %s\n", cudaGetErrorString(code));
    }

    auto stop = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> duration = stop - start;
    std::cout << "duration: " << duration.count()*1000.0 << std::endl;
    // milliseconds
    float kernel_time = 0;
    cudaEventElapsedTime(&kernel_time, e_start, e_stop);
    std::cout << "kernel_time: " << kernel_time << std::endl;

    cudaMemcpy(h_c, d_c, size*sizeof(int), cudaMemcpyDeviceToHost);

#ifdef VERIFY
    verify(n, h_a, h_b, h_c);
#endif

    cudaFree(d_a);
    cudaFree(d_b);
    cudaFree(d_c);
}