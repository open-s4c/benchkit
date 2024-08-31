
__kernel void add(
    __global float* x,
    __global float* y) {
    unsigned int idx = get_global_id(0);
    y[idx] = x[idx] + y[idx];
}