# Copyright (C) 2024 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import random
import re
import time
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils import systemactions
from benchkit.utils.dir import caller_dir
from benchkit.utils.types import PathType


class CloudsuiteBench(Benchmark):
    """
    Benchmark object for Cloudsuite benchmark suite.
    """

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper],
        command_attachments: Iterable[CommandAttachment],
        shared_libs: Iterable[SharedLib],
        pre_run_hooks: Iterable[PreRunHook],
        post_run_hooks: Iterable[PostRunHook],
        platform: Platform | None = None,
        server_platform: Platform | None = None,
        web_server_platform: Platform | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )

        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform
        self.server_platform = server_platform
        self.web_server_platform = web_server_platform

        bench_src_path = pathlib.Path(src_dir)
        dockerfile_path = bench_src_path / "benchmarks/web-serving/db_server/Dockerfile"

        dir_is_present = self.platform.comm.isdir(bench_src_path)
        dockerfile_is_present = self.platform.comm.isfile(dockerfile_path)

        if not (dir_is_present and dockerfile_is_present):
            raise ValueError(
                f"Invalid Cloudsuite source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path

        self._data_dir = pathlib.Path("/tmp/benchkit_cloudsuite")

        self.platform.comm.makedirs(self._data_dir, exist_ok=True)

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            "generator_seed",
            "nb_threads",
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "nb_threads",
        ]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("libhwloc-dev"),
        ]

    def build_tilt(self, **kwargs) -> None:
        raise NotImplementedError("Tilt is not necessary for this benchmark.")

    def prebuild_bench(
        self,
        **_kwargs,
    ) -> None:
        pass

    def build_bench(  # pylint: disable=arguments-differ
        self,
        nb_threads: int = 2,
        generator_seed: int = 0,
        **_kwargs,
    ) -> None:
        random.seed(generator_seed)
        seeds = [random.randrange(2**20 - 1) for _ in range(0, nb_threads)]

        seed_lines = [f"SEED{i}={s}" for i, s in enumerate(seeds)]
        seed_str = "\n".join(seed_lines) + "\n"
        seed_filename = self._data_dir / "_tmp_benchkit_seeds.txt"
        self.platform.comm.write_content_to_file(content=seed_str, output_filename=seed_filename)

        # Step 1 -- Build cloudsuite's faban-client docker with fabandriver.jar

        src_faban = self.bench_src_path / "benchmarks/web-serving/faban_client/"

        fabandriver_jar_file = caller_dir() / "files/fabandriver.jar"
        jar_file = fabandriver_jar_file

        # Step 1a) Move fabandriver.jar and Web20Driver.java.in into the 4 places
        self.platform.comm.copy_from_host(
            source=jar_file,
            destination=src_faban / "files/web20_benchmark/src/workload/driver/Web20Driver.java.in",
        )

        self.platform.comm.copy_from_host(
            source=jar_file,
            destination=src_faban / "files/fabandriver.jar",
        )

        self.platform.comm.copy_from_host(
            source=jar_file,
            destination=src_faban / "files/web20_benchmark/build/fabandriver.jar",
        )

        self.platform.comm.copy_from_host(
            source=jar_file,
            destination=src_faban / "files/web20_benchmark/lib/fabandriver.jar",
        )

        # Step 1b) Docker build
        self.platform.comm.shell(
            command="docker build --network=host --tag faban_built .",
            current_dir=src_faban,
        )

        # Step 2 -- Create docker container for database with pre-filled 2GB of data

        # Step 2a) Check if container is already built
        which_images = self.server_platform.comm.shell(
            command="docker images",
            print_input=False,
            print_output=False,
        )

        if "db_built" in which_images:
            print("[WARNING!!!] db_built docker is already built, skipping build_bench")
            return

        # Step 2b) Make sure that no temporary container exists by running `stop` and `rm`
        self.server_platform.comm.shell(
            command="docker stop tmp_db_server",
            ignore_ret_codes=[1],
        )
        self.server_platform.comm.shell(
            command="docker container rm tmp_db_server",
            ignore_ret_codes=[1],
        )

        # Step 2c) Create and pre-fill database server
        self.server_platform.comm.shell(
            command=[
                "docker",
                "run",
                "-dt",
                "--net=host",
                "--name=tmp_db_server",
                "cloudsuite/web-serving:db_server",
            ]
        )

        # Step 2d) Wait until initialization/pre-filling of database container is finished
        while True:
            time.sleep(1)

            docker_logs = self.server_platform.comm.pipe_shell(
                command="docker logs tmp_db_server | tac | awk '/exit/ {exit} 1' | tac",
                print_command=False,
            )

            mariadb_init_str = "Starting MariaDB database server mariadbd"
            if mariadb_init_str in docker_logs:
                docker_logs_tail = docker_logs.split(mariadb_init_str)[-1]
                break

        if "fail" in docker_logs_tail:
            raise ValueError(
                "MariaDB failed to start. Check if another container is already running."
            )

        # Step 2e) Stop container
        self.server_platform.comm.shell(command="docker stop tmp_db_server")

        # Step 2f) Commit container (in order to keep pre-filled data)
        self.server_platform.comm.shell(
            command=[
                "docker",
                "commit",
                "--change",
                "ENTRYPOINT service mariadb start && bash",
                "tmp_db_server",
                "db_built",
            ]
        )

    def clean_bench(self) -> None:
        pass

    def _clean_run(self) -> None:
        systemactions.drop_caches(comm_layer=self.platform.comm)
        systemactions.drop_caches(comm_layer=self.server_platform.comm)
        systemactions.drop_caches(comm_layer=self.web_server_platform.comm)

        self.web_server_platform.comm.shell(
            command="docker stop web_server memcache_server",
            ignore_ret_codes=[1],
        )
        self.web_server_platform.comm.shell(
            command="docker container rm memcache_server web_server",
            ignore_ret_codes=[1],
        )

        self.server_platform.comm.shell(
            command="docker stop database_server",
            ignore_ret_codes=[1],
        )
        self.server_platform.comm.shell(
            command="docker container rm database_server",
            ignore_ret_codes=[1],
        )

        self.platform.comm.shell(
            command="docker stop faban_client",
            ignore_ret_codes=[1],
        )
        self.platform.comm.shell(
            command="docker container rm faban_client",
            ignore_ret_codes=[1],
        )

    def _build_run(
        self,
        nb_threads: int,
    ) -> None:
        ip_web_server = self.web_server_platform.comm.ip_address

        self.web_server_platform.comm.shell(
            command=[
                "docker",
                "run",
                "-dt",
                "--net=host",
                "--name=memcache_server",
                "cloudsuite/web-serving:memcached_server",
            ]
        )
        self.web_server_platform.comm.shell(
            command=[
                "docker",
                "run",
                "-dt",
                "--net=host",
                "--name=web_server",
                "cloudsuite/web-serving:web_server",
                "/etc/bootstrap.sh",
                "http",
                f"{ip_web_server}",
                "172.17.0.1",  # docker address to workaround loopback bug
                f"{ip_web_server}",
                f"{nb_threads}",
                f"{nb_threads}",
            ],
        )

        self.server_platform.comm.shell(
            command="docker run -dt --net=host --name=database_server db_built"
        )

        while True:
            time.sleep(1)

            docker_logs = self.server_platform.comm.pipe_shell(
                command="docker logs database_server | tac | awk '/exit/ {exit} 1' | tac",
                print_command=False,
            )

            if "Starting MariaDB database server mariadbd" in docker_logs:
                break

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        nb_threads: int = 2,
        **kwargs,
    ) -> str:
        ip_web_server = self.web_server_platform.comm.ip_address

        self._clean_run()
        self._build_run(nb_threads)

        ping_values = self.platform.comm.shell(
            command=f"ping -c 5 {ip_web_server}",
            print_input=False,
            print_output=False,
        )

        environment = self._preload_env(
            **kwargs,
        )

        has_container = self.platform.comm.pipe_shell(
            command="docker container ls -a | grep faban_client | wc -l", ignore_ret_codes=[1]
        )

        if "1" in has_container:
            run_command = [
                "docker",
                "start",
                "-i",
                "faban_client",
            ]
        else:
            faban_output_dir = self._data_dir / "faban_output"
            seeds_file = self._data_dir / "_tmp_benchkit_seeds.txt"

            run_command = [
                "docker",
                "run",
                "--net=host",
                "--name=faban_client",
                "-v",
                f"{faban_output_dir}:/web20_benchmark/output",
                "--env-file",
                f"{seeds_file}",
                "faban_built",
                f"{ip_web_server}",
                f"{nb_threads}",
                f"--ramp-up={nb_threads + 20}",
                f"--steady={benchmark_duration_seconds}",
                "--oper=run",
            ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._bench_src_path,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        return f"{ping_values}\n{output}"

    def get_details(  # pylint: disable=arguments-differ
        self,
        record_data_dir: PathType,
        nb_threads: int,
    ) -> None:
        faban_output_dir = self._data_dir / "faban_output"

        output_dir = faban_output_dir / f"TH_{nb_threads}-TM_1000-TY_THINKTIME-DS_fixed"
        filename = output_dir / "1/detail.xan"

        file_content = self.platform.comm.read_file(path=filename)

        self._write_to_record_data_dir(file_content, "detail.xan", record_data_dir)

        trash_dir = pathlib.Path("/tmp/benchkit/.trash")
        trashed_file = trash_dir / output_dir.name
        self.platform.comm.makedirs(path=trash_dir, exist_ok=True)
        self.platform.comm.shell(
            f"sudo mv {output_dir} {trashed_file}",
            print_input=False,
            print_output=False,
        )

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        benchmark_duration_seconds: int,
        record_data_dir: PathType,
        **kwargs,
    ) -> Dict[str, Any]:
        thr = re.search(
            r".*<driverSummary.*?"
            r"<metric unit=(.*?)>(?P<throughput>.*?)<"
            r".*?<startTime>(?P<time>.*?)<"
            r".*?<totalOps unit=(.*?)>(?P<operations>.*?)<"
            r".*?<rtXtps>(?P<rtXtps>.*?)<",
            command_output,
            flags=re.DOTALL,
        )

        pattern = r"<operation name=(.*?)>.*?" r"avg(.*?)/.*?" r"max(.*?)/.*?" r"sd(.*?)/"

        m = re.findall(
            pattern,
            command_output,
            flags=re.DOTALL,
        )

        record_results = {
            "run": thr.group("time"),
            "throughput": thr.group("throughput"),
            "operations": thr.group("operations"),
            "rtXtps": thr.group("rtXtps"),
        }

        for op in m:
            oper, o_avg, o_max, o_sd = op
            oper = oper[1:-1]

            if o_avg != "":
                o_avg = o_avg[1:-1]
                o_max = o_max[1:-1]
                o_sd = o_sd[1:-1]
            else:
                o_avg = ""
                o_max = ""
                o_sd = ""

            record_results[f"{oper}_average"] = o_avg
            record_results[f"{oper}_max"] = o_max
            record_results[f"{oper}_sd"] = o_sd

        self.get_details(record_data_dir, kwargs["run_variables"]["nb_threads"])

        self._write_to_record_data_dir(command_output, "full_output.txt", record_data_dir)

        return record_results


def cloudsuite_campaign(
    name: str = "cloussuite_campaign",
    benchmark: Optional[CloudsuiteBench] = None,
    src_dir: Optional[PathType] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    server_platform: Platform | None = None,
    web_server_platform: Platform | None = None,
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    nb_threads: Iterable[int] = (1,),
    generator_seeds: Iterable[int] = (0,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Optional[Dict[str, Any]] = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the Cloudsuite benchmark."""

    variables = {
        "nb_threads": nb_threads,
        "generator_seed": generator_seeds,
    }

    if src_dir is None:
        raise ValueError(
            "A src_dir argument for the Cloudsuite benchmark"
            "(https://github.com/parsa-epfl/cloudsuite) must be defined manually."
        )

    if benchmark is None:
        benchmark = CloudsuiteBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
            server_platform=server_platform,
            web_server_platform=web_server_platform,
        )

    return CampaignCartesianProduct(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        constants=constants,
        debug=debug,
        gdb=gdb,
        enable_data_dir=enable_data_dir,
        continuing=continuing,
        benchmark_duration_seconds=benchmark_duration_seconds,
        results_dir=results_dir,
        pretty=pretty,
    )
