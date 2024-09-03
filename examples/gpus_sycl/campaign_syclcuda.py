#!/usr/bin/env python3

import time

from benchmarks.cuda_bench import CudaBench
from benchmarks.opcl_bench import OpclBench
from benchmarks.sycl_bench import SyclBench
from pythainer.examples.builders import get_user_gui_builder, opencl_builder
from pythainer.examples.runners import gpu_runner, personal_runner
from pythainer.runners import ConcreteDockerRunner, DockerRunner
from sycl import adaptivecpp_builder, sycl_builder

from benchkit.benchmark import CommandAttachment
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from benchkit.communication.docker import DockerCommLayer
from benchkit.platforms import Platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.dir import caller_dir
from benchkit.utils.types import PathType

GUEST_SRC_DIR = "/home/user/src"
CUDA_METRICS = []  # ["gpu__time_active", "gpu__time_duration", "gpu__compute_memory_throughput"]
SMI_METRICS = ["memory.used", "utilization.gpu", "utilization.memory"]
ENV_VARS = {}


def get_docker_platform() -> Platform:
    image_name = "syclcudabenchkit"
    builder = get_user_gui_builder(
        image_name=image_name,
        base_ubuntu_image="nvidia/cuda:12.2.0-devel-ubuntu22.04",
    )

    builder.space()
    builder.root()
    builder.desc("Remove annoying motd")
    builder.run(
        command=(
            r"find /opt/nvidia/entrypoint.d/ "
            r'\( -name "*.txt" -o -name "10-banner.sh" -o -name "12-banner.sh" \) '
            r"-exec rm {} +"
        )
    )
    builder.space()

    builder.user()
    builder.workdir("/home/user")

    builder |= sycl_builder() | adaptivecpp_builder() | opencl_builder()
    builder.space()

    builder.add_packages(["pip"])
    builder.run(command="pip install pyopencl")
    builder.user()

    builder.build()

    host_src_dir = (caller_dir() / "src").resolve()

    # runner
    docker_runner = ConcreteDockerRunner(
        image=image_name,
        environment_variables=ENV_VARS,
        volumes={f"{host_src_dir}": GUEST_SRC_DIR},
        devices=[],
        network="host",
        workdir=GUEST_SRC_DIR,
        root=True,
    )

    # for profiling
    profiling_runner = DockerRunner(
        other_options=[
            "--cap-add=SYS_ADMIN",
            "--privileged",
            # "--user=root"
        ]
    )

    docker_runner |= gpu_runner() | personal_runner() | profiling_runner

    comm = DockerCommLayer(docker_runner=docker_runner)

    platform = Platform(comm_layer=comm)
    return platform


def smi_attachment(current_dir: PathType) -> CommandAttachment:
    def _smi_attachment(
        process: AsyncProcess,
        record_data_dir: PathType,
    ) -> None:
        assert record_data_dir
        smi_command = "nvidia-smi --query-gpu memory.used,utilization.gpu,utilization.memory --format=csv -lms 20 > smi.csv & sleep 0.3; kill $!"
        while not process.is_finished():
            process._platform.comm.shell(
                command=smi_command,
                current_dir=current_dir,
                output_is_log=True,
            )
            time.sleep(0.3)

    return _smi_attachment


def main():
    runs = 3
    platform = get_docker_platform()

    attachments = [smi_attachment(current_dir=GUEST_SRC_DIR)]

    cudabench_vecadd = CudaBench(
        platform=platform,
        src_dir=f"{GUEST_SRC_DIR}/cuda/vec-add",
        file_name="add",
        command_attachments=attachments,
    )

    syclbench_vecadd = SyclBench(
        platform=platform,
        src_dir=f"{GUEST_SRC_DIR}/sycl",
        build_dir=f"{GUEST_SRC_DIR}/sycl/build",
        cmake_target="add",
        command_attachments=attachments,
    )

    opclbench_vecadd = OpclBench(
        platform=platform,
        src_dir=f"{GUEST_SRC_DIR}/opencl",
        file_name="add",
        command_attachments=attachments,
    )

    cudabench_matmul = CudaBench(
        platform=platform,
        src_dir=f"{GUEST_SRC_DIR}/cuda/mat-mul",
        file_name="matmul",
        command_attachments=attachments,
    )

    syclbench_matmul = SyclBench(
        platform=platform,
        src_dir=f"{GUEST_SRC_DIR}/sycl",
        build_dir=f"{GUEST_SRC_DIR}/sycl/build",
        cmake_target="matmul",
        command_attachments=attachments,
    )

    opclbench_matmul = OpclBench(
        platform=platform,
        src_dir=f"{GUEST_SRC_DIR}/opencl",
        file_name="matmul",
        command_attachments=attachments,
    )

    cudacampaign_vecadd = CampaignCartesianProduct(
        name="add_cuda",
        benchmark=cudabench_vecadd,
        nb_runs=runs,
        variables={"block_size": [1, 4, 8, 32, 64, 128, 256, 512, 1024]},
        constants={
            # "enable_profiling": ENABLE_PROFILING,
            "profiling_metrics": CUDA_METRICS,
            "smi_metrics": SMI_METRICS,
        },
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    syclcampaign_vecadd = CampaignCartesianProduct(
        name="add_sycl",
        benchmark=syclbench_vecadd,
        nb_runs=runs,
        variables={"block_size": [1, 4, 8, 32, 64, 128, 256, 512, 1024]},
        constants={"profiling_metrics": CUDA_METRICS, "smi_metrics": SMI_METRICS},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    opclcampaign_vecadd = CampaignCartesianProduct(
        name="add_opcl",
        benchmark=opclbench_vecadd,
        nb_runs=runs,
        variables={"block_size": [1, 4, 8, 32, 64, 128, 256, 512, 1024]},
        constants={"smi_metrics": SMI_METRICS},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    cudacampaign_matmul = CampaignCartesianProduct(
        name="matmul_cuda",
        benchmark=cudabench_matmul,
        nb_runs=runs,
        variables={"block_size": [1, 2, 4, 8, 16, 32]},
        constants={"profiling_metrics": CUDA_METRICS, "smi_metrics": SMI_METRICS},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    syclcampaign_matmul = CampaignCartesianProduct(
        name="matmul_sycl",
        benchmark=syclbench_matmul,
        nb_runs=runs,
        variables={"block_size": [1, 2, 4, 8, 16, 32]},
        constants={"profiling_metrics": CUDA_METRICS, "smi_metrics": SMI_METRICS},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    opclcampaign_matmul = CampaignCartesianProduct(
        name="matmul_opcl",
        benchmark=opclbench_matmul,
        nb_runs=runs,
        variables={"block_size": [1, 2, 4, 8, 16, 32]},
        constants={"smi_metrics": SMI_METRICS},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=None,
    )

    start_time = time.time()
    suite_vecadd = CampaignSuite(
        campaigns=[
            cudacampaign_vecadd,
            syclcampaign_vecadd,
            opclcampaign_vecadd,
        ]
    )
    suite_matmul = CampaignSuite(
        campaigns=[
            cudacampaign_matmul,
            syclcampaign_matmul,
            opclcampaign_matmul,
        ]
    )
    suite_vecadd.print_durations()
    suite_matmul.print_durations()
    suite_vecadd.run_suite()
    suite_matmul.run_suite()
    stop_time = time.time()
    print("benchmark duration:", stop_time - start_time)

    suite_vecadd.generate_graph(
        plot_name="barplot",
        title=f"vector add duration",
        y="duration",
        x="block_size",
        hue="benchname",
    )

    suite_vecadd.generate_graph(
        plot_name="barplot",
        title=f"vector add kernel time",
        y="kernel_time",
        x="block_size",
        hue="benchname",
    )

    suite_vecadd.generate_graph(
        plot_name="barplot",
        title="vector add gpu usage",
        y="utilization.gpu",
        x="block_size",
        hue="benchname",
    )

    suite_matmul.generate_graph(
        plot_name="barplot",
        title="vector add vram usage",
        y="memory.used",
        x="block_size",
        hue="benchname",
    )

    suite_matmul.generate_graph(
        plot_name="barplot",
        title="matrix multiplication duration",
        y="duration",
        x="block_size",
        hue="benchname",
    )

    suite_matmul.generate_graph(
        plot_name="barplot",
        title="matrix multiplication kernel time",
        y="kernel_time",
        x="block_size",
        hue="benchname",
    )

    suite_matmul.generate_graph(
        plot_name="barplot",
        title="matrix multiplication gpu usage",
        y="utilization.gpu",
        x="block_size",
        hue="benchname",
    )

    suite_matmul.generate_graph(
        plot_name="barplot",
        title="matrix multiplication vram usage",
        y="memory.used",
        x="block_size",
        hue="benchname",
    )


if __name__ == "__main__":
    main()
