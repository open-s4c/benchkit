from pythainer.builders import PartialDockerBuilder
from pythainer.builders.utils import project_git_cmake_build_install


def adaptivecpp_builder() -> PartialDockerBuilder:
    builder = PartialDockerBuilder()
    project_git_cmake_build_install(
        builder=builder,
        workdir="/home/user/AdaptiveCpp",
        git_url="https://github.com/AdaptiveCpp/AdaptiveCpp",
        commit="fca4859",
        cmake_options={"WITH_CUDA_BACKEND": "ON"},
    )
    return builder


def sycl_builder() -> PartialDockerBuilder:
    builder = PartialDockerBuilder()
    builder.space()
    builder.root()
    builder.add_packages(
        packages=[
            "lsb-release",
            "wget",
            "software-properties-common",
            "gnupg",
            "python3",
            "cmake",
            "libboost-all-dev",
            "build-essential",
        ]
    )
    builder.run_multiple(
        commands=[
            "wget https://apt.llvm.org/llvm.sh",
            "chmod +x llvm.sh",
            "sudo ./llvm.sh 16",
        ]
    )
    builder.add_packages(
        packages=[
            "libclang-16-dev",
            "clang-tools-16",
            "libomp-16-dev",
            "llvm-16-dev",
            "lld-16",
        ]
    )
    builder.user()
    return builder
