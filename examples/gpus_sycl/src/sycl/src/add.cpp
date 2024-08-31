
#include <CL/sycl.hpp>
using namespace cl;

using data_type = float;

#ifndef WGROUP_SIZE
#define WGROUP_SIZE 1024
#endif

std::vector<data_type> add(cl::sycl::queue &q,
                           int n,
                           std::vector<data_type> &a,
                           std::vector<data_type> &b)
{
    assert(a.size() == b.size());
    {
        sycl::buffer<data_type> buff_a(a.data(), a.size());
        sycl::buffer<data_type> buff_b(b.data(), b.size());

        auto local_range = sycl::range<1>(WGROUP_SIZE);
        auto global_range = sycl::range<1>(n);
        auto nd_range = sycl::nd_range(global_range, local_range);

        auto start = std::chrono::high_resolution_clock::now();

        auto event_start = q.submit([&](sycl::handler &cgh)// command group handler
                 {
        auto acc_a = buff_a.get_access<sycl::access::mode::read>(cgh);
        auto acc_b = buff_b.get_access<sycl::access::mode::read_write>(cgh);

        cgh.parallel_for<class vector_add>(nd_range, [=](sycl::nd_item<1> item) {
                int idx = item.get_global_id(0);
                acc_b[idx] = acc_a[idx] + acc_b[idx];
            }
        );
        });

    // q.wait();
    event_start.wait();
    auto stop = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = stop - start;
    std::cout << "duration: " << elapsed.count()*1000.0f << std::endl;
    auto submit_time = event_start.get_profiling_info<sycl::info::event_profiling::command_submit>();
    auto e_start = event_start.get_profiling_info<sycl::info::event_profiling::command_start>();
    auto e_end = event_start.get_profiling_info<sycl::info::event_profiling::command_end>();
    auto start_delay = (e_start - submit_time) / 1000000.0;
    // milliseconds
    auto kernel_time = (e_end - e_start) / 1000000.0;
    std::cout << "start_delay: " << start_delay << std::endl;
    std::cout << "kernel_time: " << kernel_time << std::endl;
    }
    return b;
}

int main()
{
    int n = 1<<25;
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
    std::cout << "Running on "
              << q.get_device().get_info<sycl::info::device::name>()
              << "\n"
              << "local mem size"       << q.get_device().get_info<sycl::info::device::local_mem_size>() << "\n"
              << "global mem size"       << q.get_device().get_info<sycl::info::device::global_mem_size>() << "\n"
              << "work group size"      << q.get_device().get_info<sycl::info::device::max_work_group_size>() << "\n"
              << "compute units"        << q.get_device().get_info<sycl::info::device::max_compute_units>() << "\n"
              << "work item dimensions" << q.get_device().get_info<sycl::info::device::max_work_item_dimensions>() << "\n";
    std::vector<data_type> a(n, 1.0f);
    std::vector<data_type> b(n, 2.0f);
    auto res = add(q, n, a, b);

    return 0;
}
