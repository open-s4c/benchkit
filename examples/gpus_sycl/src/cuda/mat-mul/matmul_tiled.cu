
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
    __shared__ int a_work[BLOCK_SIZE*BLOCK_SIZE];
    __shared__ int b_work[BLOCK_SIZE*BLOCK_SIZE];

    int tx = threadIdx.x;
    int ty = threadIdx.y;
    // global idx
    int x = blockIdx.x * blockDim.x + tx;
    int y = blockIdx.y * blockDim.y + ty;

    int tmp = 0;
    // i -> 1024/16 = 64 blocks across
    for (int i=0; i<n/BLOCK_SIZE; i++) {
        a_work[ty*BLOCK_SIZE+tx] = a[y*n + i*BLOCK_SIZE + tx];
        b_work[ty*BLOCK_SIZE+tx] = b[(ty+i*BLOCK_SIZE)*n + x];

        __syncthreads(); // wait for full block

        for (int j=0; j<BLOCK_SIZE; j++) {
            tmp += a_work[ty*BLOCK_SIZE+j] * b_work[j*BLOCK_SIZE+tx];
        }
        __syncthreads();
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

    int numBlocks = (n + BLOCK_SIZE - 1) / BLOCK_SIZE;
    dim3 dimGrid(numBlocks, numBlocks, 1);
    dim3 dimBlock(BLOCK_SIZE, BLOCK_SIZE, 1);
    printf("%d %d\n", BLOCK_SIZE, numBlocks);

    for (int i=0; i<size; i++) {
        h_a[i] = 1;//i;
        h_b[i] = 1;//i;
    }
    // copy over
    cudaMemcpy(d_a, h_a, size*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, size*sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(d_c, h_c, size*sizeof(int), cudaMemcpyHostToDevice);

    auto start = std::chrono::high_resolution_clock::now();
    matmul<<<dimGrid, dimBlock>>>(n, d_a, d_b, d_c);
    cudaDeviceSynchronize();
    auto stop = std::chrono::high_resolution_clock::now();

    cudaError_t code = cudaPeekAtLastError();
    if (code != cudaSuccess) {
        fprintf(stderr,"GPUassert: %s\n", cudaGetErrorString(code));
    }

    std::chrono::duration<double> duration = stop - start;
    std::cout << "duration: " << duration.count() << std::endl;

    cudaMemcpy(h_c, d_c, size*sizeof(int), cudaMemcpyDeviceToHost);

#ifdef VERIFY
    verify(n, h_a, h_b, h_c);
#endif

    cudaFree(d_a);
    cudaFree(d_b);
    cudaFree(d_c);
}