/*
 * This file is based on the tutorial available on NVIDIA website:
 * https://developer.nvidia.com/blog/even-easier-introduction-cuda/
 */

#include <iostream>
#include <math.h>
#include <chrono>

#ifndef BLOCK_SIZE
#define BLOCK_SIZE 256
#endif /* BLOCK_SIZE */

// Kernel function to add the elements of two arrays
__global__
void add(int n, float *x, float *y)
{
  int index = blockIdx.x * blockDim.x + threadIdx.x;
  int stride = blockDim.x * gridDim.x;
  for (int i = index; i < n; i += stride)
    y[i] = x[i] + y[i];
}

int main(void)
{
  int N = 1<<25;
  float *x, *y;
  const int blockSize = BLOCK_SIZE;
  const int numBlocks = (N + blockSize - 1) / blockSize;

  std::cout << "Add vector benchmark." << std::endl;
  std::cout << "Inputs:" << std::endl;
  std::cout << "  blockSize: " << blockSize << std::endl;
  std::cout << "  numBlocks: " << numBlocks << std::endl;

  // Allocate Unified Memory – accessible from CPU or GPU
  cudaMallocManaged(&x, N*sizeof(float));
  cudaMallocManaged(&y, N*sizeof(float));

  // initialize x and y arrays on the host
  for (int i = 0; i < N; i++) {
    x[i] = 1.0f;
    y[i] = 2.0f;
  }

  auto start = std::chrono::high_resolution_clock::now();

  // Run kernel on N elements on the GPU
  add<<<numBlocks, blockSize>>>(N, x, y);

  // Wait for GPU to finish before accessing on host
  cudaDeviceSynchronize();

  auto stop = std::chrono::high_resolution_clock::now();
  std::chrono::duration<double> elapsed_time = stop - start;

  // Check for errors (all values should be 3.0f)
  std::cout << "Outputs:" << std::endl;
  float maxError = 0.0f;
  for (int i = 0; i < N; i++)
    maxError = fmax(maxError, fabs(y[i]-3.0f));
  std::cout << "  max_error: " << maxError << std::endl;
  std::cout << "  kernel_compute_seconds: " << elapsed_time.count() << std::endl;

  // Free memory
  cudaFree(x);
  cudaFree(y);

  return 0;
}
