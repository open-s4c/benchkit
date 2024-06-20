from benchkit.communication import LocalCommLayer, SSHCommLayer
from benchkit.communication.docker import DockerCommLayer

import os
import pathlib


host_dir = pathlib.Path("/tmp/benchkit/host_files")
remote = "ssh://localhost:2222/"


def host_prepare_files():
    if not host_dir.is_dir():
        os.makedirs(host_dir)

    for i in range(1, 4, 1):
        with open(host_dir/f"file{i}", "w") as f:
            f.write(f"file{i}\n")


def main():
    host_prepare_files()

    local_comm = LocalCommLayer()
    local_target_dir = pathlib.Path("/tmp/benchkit/target_local_files")
    local_download_dir = pathlib.Path("/tmp/benchkit/dl_local_files")
    local_comm.copy_from_host(source=f"{host_dir}/", destination=f"{local_target_dir}/")
    local_comm.copy_to_host(source=f"{local_target_dir}/", destination=f"{local_download_dir}/")

    ssh_comm = SSHCommLayer(host=remote, environment=None)
    ssh_target_dir = pathlib.Path("/tmp/benchkit/target_ssh_files")
    ssh_comm.copy_from_host(source=f"{host_dir}/", destination=f"{ssh_target_dir}/")
    ssh_download_dir = pathlib.Path("/tmp/benchkit/dl_ssh_files")
    ssh_comm.copy_to_host(source=f"{ssh_target_dir}/", destination=f"{ssh_download_dir}/")

    # TODO: implement for Docker comm layer
    # docker_comm = DockerCommLayer()
    # docker_target_dir = pathlib.Path("/tmp/benchkit/target_docker_files")
    # docker_comm.copy_from_host(source=f"{host_dir}/", destination=f"{docker_target_dir}/")
    # docker_download_dir = pathlib.Path("/tmp/benchkit/dl_docker_files")
    # docker_comm.copy_to_host(source=f"{docker_target_dir}/", destination=f"{docker_download_dir}/")


if __name__ == '__main__':
    main()
