
#include <CL/sycl.hpp>
using namespace cl;

using data_type = int;

#ifndef WGROUP_SIZE
#define WGROUP_SIZE 32
#endif

void matmul(sycl::queue &q,
    int n,
    const std::vector<data_type> &a,
    const std::vector<data_type> &b,
    const std::vector<data_type> &c) {
    
    sycl::buffer<data_type, 2> buff_a(a.data(), sycl::range(n, n));
    sycl::buffer<data_type, 2> buff_b(b.data(), sycl::range(n, n));
    sycl::buffer<data_type, 2> buff_c(c.data(), sycl::range(n, n));

    auto local_range = sycl::range(WGROUP_SIZE, WGROUP_SIZE);

    auto global_range = sycl::range(n, n);
    auto nd_range = sycl::nd_range(global_range, local_range);

    auto start = std::chrono::high_resolution_clock::now();

    auto event_start = q.submit([&](sycl::handler &cgh) {
        auto acc_a = buff_a.get_access<sycl::access::mode::read>(cgh);
        auto acc_b = buff_b.get_access<sycl::access::mode::read>(cgh);
        auto acc_c = buff_c.get_access<sycl::access::mode::write>(cgh);

        cgh.parallel_for(nd_range, [=](sycl::nd_item<2> item){
            int i = item.get_global_id(0); // r
            int j = item.get_global_id(1); // c
            int tmp = 0;
            for (int k=0; k<n; k++) {
                tmp += acc_a[j][k] * acc_b[k][i];
            }
            acc_c[j][i] = tmp;
        });
    });
    event_start.wait();
    q.wait();
    auto stop = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = stop - start;
    auto submit_time = event_start.get_profiling_info<sycl::info::event_profiling::command_submit>();
    auto e_start = event_start.get_profiling_info<sycl::info::event_profiling::command_start>();
    auto e_end = event_start.get_profiling_info<sycl::info::event_profiling::command_end>();
    auto start_delay = (e_start - submit_time) / 1000000.0;
    auto kernel_time = (e_end - e_start) / 1000000.0;
    std::cout << "duration: " << elapsed.count()*1000.0f << std::endl;
    std::cout << "kernel_time: " << kernel_time << std::endl;
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
    auto exception_handler = [] (sycl::exception_list excs) {
        for (std::exception_ptr const& e : excs) {
            try {
                std::rethrow_exception(e);
            } catch(sycl::exception const& e) {
                std::cout << "async SYCL exception:\n"
                << e.what() << std::endl;
            }
        }
    };
    auto property_list = sycl::property_list{
        sycl::property::queue::enable_profiling(),
        sycl::property::queue::in_order()};
    sycl::queue q(sycl::default_selector(), exception_handler, property_list);
    std::vector<data_type> a(size, 1);
    std::vector<data_type> b(size, 2);
    std::vector<data_type> c(size, 0);

    matmul(q, n, a, b, c);

#ifdef VERIFY
    verify(n, a.data(), b.data(), c.data());
#endif
    return 0;
}