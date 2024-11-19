# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
from typing import Any, Dict, Iterable, List, Optional

import time
import re
import random

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils import systemactions
from benchkit.utils.types import CpuOrder, PathType


class CloudsuiteBench(Benchmark):
    """
    Benchmark object for Cloudsuite benchmark suite.
    """

    def __init__(
        self,
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

    @property
    def bench_src_path(self) -> pathlib.Path:
        return None

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            "generator_seed",
            "nb_threads",
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            #TODO: Add benchmark as a variable
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

    def _build_bench(
        self,
        nb_threads: int,
    ) -> None:
        mariadb_initialized = False

        ip_web_server = self.web_server_platform.comm.get_ipaddress
        ip_server = self.server_platform.comm.get_ipaddress

        self.web_server_platform.comm.shell(command="sudo systemctl restart cntlm")
        self.server_platform.comm.shell(command="sudo systemctl restart cntlm")
        self.platform.comm.shell(command="sudo systemctl restart cntlm")

        self.web_server_platform.comm.shell(
            command="docker run -dt --net=host --name=memcache_server cloudsuite/web-serving:memcached_server"
        )
        self.web_server_platform.comm.shell(
            command=f"docker run -dt --net=host --name=web_server cloudsuite/web-serving:web_server /etc/bootstrap.sh http {ip_web_server} {ip_server} {ip_web_server} {nb_threads} {nb_threads}"
        )

        self.server_platform.comm.shell(
            command="docker run -dt --net=host --name=database_server db_server_filled"
        )

        command = "docker logs database_server | tac | awk '/exit/ {exit} 1' | tac"

        while not mariadb_initialized:
            time.sleep(1)

            ret = self.server_platform.comm.pipe_shell(
                command=command,
            )

            if "Starting MariaDB database server mariadbd" in ret:
                mariadb_initialized = True

        self.web_server_platform.comm.shell(command="sudo systemctl stop cntlm")
        self.server_platform.comm.shell(command="sudo systemctl stop cntlm")
        self.platform.comm.shell(command="sudo systemctl stop cntlm")

        #mariadb_threads = self.server_platform.comm.pipe_shell(command="ps ax -T | grep mariad | grep sock")
        #for line in mariadb_threads.strip().split('\n'):
        #    if line.strip() == []:
        #        continue
        #   tid = line.strip().split()[1]

        #   self.server_platform.comm.shell(
        #       command=f"sudo taskset -cp 0-95 {tid}",
        #       ignore_ret_codes=[1]
        #   )

    def build_bench(  # pylint: disable=arguments-differ
        self,
        nb_threads: int = 2,
        generator_seed: int = 0,
        **_kwargs,
    ) -> None:

        random.seed(generator_seed)
        seeds = [random.randrange(2 ** 20 - 1) for j in range(0, nb_threads)]

        seeds_str = ""

        for i, s in enumerate(seeds):
            seeds_str = seeds_str + f"SEED{i}={s}\\\\n"

        self.platform.comm.shell(
            command=f"printf {seeds_str} > _tmp_benchkit_seeds.txt",
            current_dir="~/",
        )

    def _clean_bench(self) -> None:
        systemactions.drop_caches(comm_layer=self.platform.comm)
        systemactions.drop_caches(comm_layer=self.server_platform.comm)
        systemactions.drop_caches(comm_layer=self.web_server_platform.comm)

        self.web_server_platform.comm.shell(command="docker stop web_server memcache_server", ignore_ret_codes=[1])
        self.web_server_platform.comm.shell(command="docker container rm memcache_server web_server", ignore_ret_codes=[1])

        self.server_platform.comm.shell(command="docker stop database_server", ignore_ret_codes=[1])
        self.server_platform.comm.shell(command="docker container rm database_server", ignore_ret_codes=[1])

        self.platform.comm.shell(command="docker stop faban_client", ignore_ret_codes=[1])
        self.platform.comm.shell(command="docker container rm faban_client", ignore_ret_codes=[1])

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        nb_threads: int = 2,
        **kwargs,
    ) -> str:

        ip_web_server = self.web_server_platform.comm.get_ipaddress

        self._clean_bench()
        self._build_bench(nb_threads)

        ping_values = self.platform.comm.shell(
            command=f"ping -c 5 {ip_web_server}",
            print_input = False,
            print_output = False,
        )

        environment = self._preload_env(
            **kwargs,
        )
        
        has_container = self.platform.comm.pipe_shell(command="docker container ls -a | grep faban_client | wc -l", ignore_ret_codes=[1])

        if '1' in has_container:
            run_command = [
                "docker",
                "start",
                "-i",
                "faban_client",
            ]
        else:
            run_command = [
                "docker",
                "run",
                "--net=host",
                "--name=faban_client",
                "-v",
                "/home/drc/rchehab/faban_output/:/web20_benchmark/output",
                "--env-file",
                "_tmp_benchkit_seeds.txt",
                #"try_faban",
                "try_faban_debug",
                f"{ip_web_server}",
                f"{nb_threads}",
                f"--ramp-up={benchmark_duration_seconds + 20}",
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
            current_dir="~/",
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )

        return f"{ping_values}\n{output}"

    def get_details(  # pylint: disable=arguments-differ
        self,
        record_data_dir: PathType,
    ) -> None:
        filename="/home/drc/rchehab/faban_output/TH_*-TM_1000-TY_THINKTIME-DS_fixed/*/detail.xan"
        filename_dir="/home/drc/rchehab/faban_output/TH_*-TM_1000-TY_THINKTIME-DS_fixed"

        file_content = self.platform.comm.shell(
            f"cat {filename}",
            print_input=False,
            print_output=False,
        )

        self._write_to_record_data_dir(file_content, "detail.xan", record_data_dir)

        self.platform.comm.shell(
            f"sudo rm -rf {filename_dir}",
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
            r".*?<rtXtps>(?P<rtXtps>.*?)<"
            ,
            command_output,
            flags=re.DOTALL,
        )

        pattern = ( 
            r"<operation name=(.*?)>.*?"
            r"avg(.*?)/.*?"
            r"max(.*?)/.*?"
            r"sd(.*?)/"
        )

        m = re.findall(
            pattern,
            command_output,
            flags=re.DOTALL,
        )

        add_to_csv = {
            "run": thr.group("time"),
            "throughput": thr.group("throughput"),
            "operations": thr.group("operations"),
            "rtXtps": thr.group("rtXtps"),
        }

        for op in m:
            oper, o_avg, o_max, o_sd = op
            oper = oper[1:-1]

            if o_avg != '':
                o_avg = o_avg[1:-1]
                o_max = o_max[1:-1]
                o_sd = o_sd[1:-1]
            else:
                o_avg = ""
                o_max = ""
                o_sd = ""

            add_to_csv[f"{oper}_average"] = o_avg
            add_to_csv[f"{oper}_max"] = o_max
            add_to_csv[f"{oper}_sd"] = o_sd

        self.get_details(record_data_dir)

        self._write_to_record_data_dir(command_output, "full_output.txt", record_data_dir)

        return add_to_csv

def cloudsuite_campaign(
    name: str = "cloussuite_campaign",
    benchmark: Optional[CloudsuiteBench] = None,
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

    if benchmark is None:
        benchmark = CloudsuiteBench(
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
        pretty=None,
    )
