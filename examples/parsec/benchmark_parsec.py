# Copyright (C) 2026 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType

supported_bench_names = [
    "blackscholes",
    "bodytrack",
    "canneal",
    "dedup",
    "facesim",
    "ferret",
    "fluidanimate",
    "freqmine",
    "netdedup",
    "netferret",
    "netstreamcluster",
    "raytrace",
    "streamcluster",
    "swaptions",
    "vips",
    "x264",
    "splash2.barnes",
    "splash2.cholesky",
    "splash2.fft",
    "splash2.fmm",
    "splash2.lu_cb",
    "splash2.lu_ncb",
    "splash2.ocean_cp",
    "splash2.ocean_ncp",
    "splash2.radiosity",
    "splash2.radix",
    "splash2.raytrace",
    "splash2.volrend",
    "splash2.water_nsquared",
    "splash2.water_spatial",
    "splash2x.barnes",
    "splash2x.cholesky",
    "splash2x.fft",
    "splash2x.fmm",
    "splash2x.lu_cb",
    "splash2x.lu_ncb",
    "splash2x.ocean_cp",
    "splash2x.ocean_ncp",
    "splash2x.radiosity",
    "splash2x.radix",
    "splash2x.raytrace",
    "splash2x.volrend",
    "splash2x.water_nsquared",
    "splash2x.water_spatial",
]


class ParsecBench(Benchmark):
    """Benchmark object for PARSEC benchmarks."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform | None = None,
        clean_in_between_different_benchmarks: bool = False,
        # build_dir: PathType | None = None,
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

        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path):
            raise ValueError(
                f"Invalid PARSEC source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path
        self.clean_in_between_different_benchmarks = clean_in_between_different_benchmarks

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return [
            "bench_name",
        ]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "bench_name",
            "nb_threads",
            "input",
        ]

    @staticmethod
    def _parse_results(
        output: str,
        bench_name: str,
        nb_threads: int,
    ) -> Dict[str, str]:
        duration = ""
        for line in output.split("\n"):

            output_exceptions = ["lusearch"]
            if bench_name in output_exceptions and line.startswith("===== DaCapo processed"):
                splits = line.split(" ")
                duration = splits[6]
            elif (
                bench_name not in output_exceptions
                and line.startswith("===== DaCapo")
                and "PASSED" in line
            ):
                splits = line.split(" ")
                duration = splits[6]

        return {"duration": duration}

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("openjdk-21-jdk"),
        ]

    def prebuild_bench(self, **_kwargs) -> None:
        pass

    def build_bench(
        self,
        bench_name: str,
        **kwargs,
    ) -> None:
        self.platform.comm.shell(
            command=f"parsecmgmt -a build -p {bench_name}",
            current_dir=self._bench_src_path,
            output_is_log=True,
        )

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        input: str,
        nb_threads: int,
        bench_name: str,
        **kwargs,
    ) -> str:

        pre_pre_run_ouput = self.platform.comm.shell(
            command=f"parsecmgmt -a run -p {bench_name} -n {nb_threads} -i {input}",
            current_dir=self._bench_src_path,
            output_is_log=False,
            print_output=False,
        )

        parsecdir = None
        parsecplat = None
        run_dir = None
        pre_run_command = None
        for line in pre_pre_run_ouput.splitlines():
            sline = line.strip()
            print(sline)

            if "[Benchmark PARSECDIR]" in sline:
                m = re.search(r"^.*\[Benchmark PARSECDIR\]:(\S+)\s*$", sline)
                if m:
                    parsecdir = m.group(1)

            elif "[Benchmark PARSECPLAT]" in sline:
                m = re.search(r"^.*\[Benchmark PARSECPLAT\]:(\S+)\s*$", sline)
                if m:
                    parsecplat = m.group(1)

            elif "[Benchmark Dir]" in sline:
                m = re.search(r"^.*\[Benchmark Dir\]:(\S+)\s*$", sline)
                if m:
                    run_dir = m.group(1)

            elif "[Benchmark Command]" in sline:
                m = re.search(r"^.*\[Benchmark Command\]:(.+)\s*$", sline)
                if m:
                    pre_run_command = m.group(1)

        if parsecdir is None or parsecplat is None or run_dir is None or pre_run_command is None:
            raise RuntimeError("Run dir or pre run command is empty")

        environment = self._preload_env(
            input=input,
            **kwargs,
        )

        if environment is None:
            environment = {}

        environment["PARSECDIR"] = parsecdir
        environment["PARSECPLAT"] = parsecplat

        pre_run_script = pre_run_command.split(" ")[0]

        run_command = None
        if bench_name.startswith("splash2x"):

            if not pre_run_script.endswith(".sh"):
                raise RuntimeError("The pre_run_script does not end with .sh")

            pre_run_script_path = pathlib.Path(pre_run_script)

            lines = pre_run_script_path.read_text().splitlines()

            new_lines = []
            for line in lines:
                sline = line.strip()

                if sline.startswith("echo") and "Running $RUN" in sline:
                    new_lines.append('echo "[Benchmark Run Command]:$RUN:" ')
                elif sline.startswith("eval") and "$RUN" in sline:
                    new_lines.append(":")
                else:
                    new_lines.append(line)

            pre_run_script_path.write_text("\n".join(new_lines) + "\n")

            pre_run_ouput = self.platform.comm.shell(
                command=pre_run_command,
                environment=environment,
                current_dir=run_dir,
                output_is_log=False,
                print_output=False,
            )

            for line in pre_run_ouput.splitlines():
                sline = line.strip()
                print(sline)

                if "[Benchmark Run Command]" in sline:
                    m = re.search(r"^.*\[Benchmark Run Command\]:(.+)\s*$", sline)
                    if m:
                        run_command = m.group(1).split(" ")
        else:
            run_command = pre_run_command.split(" ")

        if run_command is None:
            raise RuntimeError("Run command is empty")

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=run_dir,
            environment=environment,
            wrapped_environment=wrapped_environment,
            print_output=False,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        return {}


def parsec_campaign(
    name: str = "parsec_campaign",
    benchmark: Optional[ParsecBench] = None,
    bench_names: Iterable[str] = ("blackscholes",),
    src_dir: Optional[PathType] = None,
    # build_dir: Optional[str] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    input: Iterable[str] = ("simlarge",),
    nb_threads: Iterable[int] = (1,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    clean_in_between_different_benchmarks: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
    symlink_latest: bool = False,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the PARSEC benchmark."""
    variables = {
        "input": input,
        "nb_threads": nb_threads,
        "bench_name": bench_names,
    }
    if pretty is not None:
        pretty = {"input": pretty}

    if not all(bench_name in supported_bench_names for bench_name in bench_names):
        unsupported_benchmarks = [
            bench_name for bench_name in bench_names if bench_name not in supported_bench_names
        ]
        raise ValueError(
            f"Invalid bench_names for PARSEC: {unsupported_benchmarks}\n"
            f"The supported bench names are: {supported_bench_names}."
        )

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = ParsecBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            clean_in_between_different_benchmarks=clean_in_between_different_benchmarks,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
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
        symlink_latest=symlink_latest,
    )
