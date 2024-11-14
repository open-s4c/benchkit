
__kernel void matmul(
    __global int *a,
    __global int *b,
    __global int *c,
    int n) {
    int x = get_global_id(0);
    int y = get_global_id(1);
    int tmp = 0;
    for (int i=0; i<n; i++) {
        tmp += a[y*n+i] * b[i*n+x];
    }
    c[y*n+x] = tmp;
}