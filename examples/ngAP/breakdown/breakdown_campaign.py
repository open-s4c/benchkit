
# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Benchkit support for LevelDB benchmark.
See: https://github.com/google/leveldb
"""

import pathlib
from typing import Any, Dict, Iterable, List, Optional
from benchkit.utils.dir import get_curdir, parentdir

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignIterateVariables, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType
from benchkit.commandwrappers.ncu import NcuWrap, CommandWrapper

from parse_options import gen_dict_list

options = ['--active-threshold', '--adaptive-aas', '--add-aan-start', '--add-aas-interval', '--algorithm', '--app-name', '--block-size', '--compress-prec-table', '--data-buffer-fetch-size', '--duplicate-input-stream', '--group-num', '--input-len', '--input-start-pos', '--max-nfa-size', '--motivate-worklist-length', '--num-state-per-group', '--only-exec-cc-with-state-id', '--only-exec-ccid', '--output-file', '--padding', '--pc-use-uvm', '--precompute-cutoff', '--precompute-depth', '--quick-validation', '--quit-degree', '--remove-degree', '--report-filename', '--report-off', '--result-capacity', '--split-entire-inputstream-to-chunk-size', '--try-adaptive-aas', '--tuning', '--unique', '--unique-frequency', '--use-soa', '--use-uvm', '--validation', '-a', '-i', "--output-file", "--no-name-provided"]

class BreakdownBench(Benchmark):
    """Benchmark object for LevelDB benchmark."""

    def __init__(
        self,
        # app_name: str,
        # input_file: Optional[PathType],
        # mnrl_file: Optional[PathType],
        # anml_file: Optional[PathType],
        # hs_file: Optional[PathType],
        # quick_validation: Optional[int],
        # exclude_apps: Optional[List],
        # short_name: Optional[str] = None,
        src_path: Optional[PathType] = None,
        build_path: Optional[PathType] = None,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        if platform is not None:
            self.platform = platform

        if src_path is not None:
            self._bench_src_path = src_path
        else:
            campaign_script_path = get_curdir(__file__)
            bench_src_path = parentdir(path=campaign_script_path, levels=1) / "src"
            if not self.platform.comm.isdir(bench_src_path):
                raise ValueError(
                    f"Invalid ngAP source path: {bench_src_path}\n"
                )
            self._bench_src_path = bench_src_path

        if build_path is None:
            self._build_dir = parentdir(path=self._bench_src_path, levels=1) / "build"
        else:
            self._build_dir = build_path

        # self.app_name = app_name
        # self.input_file = input_file
        # self.mnrl_file = mnrl_file
        # self.anml_file = anml_file
        # self.hs_file = hs_file
        # self.quick_validation = quick_validation
        # self.exclude_apps = exclude_apps
        # self.short_name = short_name

        # if self.app_name in self.exclude_apps:
        #     raise ValueError(
        #         f"Cannot create a benchmark object for this app - this app is excluded: {self.app_name}"
        #     )

        # if self.input_file is not None and not self.platform.comm.isfile(self.input_file):
        #     raise ValueError(
        #         f"Invalid input stream file: {self.input_file}"
        #     )

        # if self.mnrl_file is not None and not self.platform.comm.isfile(self.mnrl_file):
        #     raise ValueError(
        #         f"Invalid mnrl file: {self.mnrl_file}"
        #     )

        # if self.anml_file is not None and not self.platform.comm.isfile(self.anml_file):
        #     raise ValueError(
        #         f"Invalid anml file: {self.anml_file}"
        #     )

        # if self.hs_file is not None and not self.platform.comm.isfile(self.hs_file):
        #     raise ValueError(
        #         f"Invalid hs file: {self.hs_file}"
        #     )

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "input_start_pos",
            "report_off",
            "split_entire_inputstream_to_chunk_size",
            "compress_prec_table",
            "data_buffer_fetch_size",
            "quit_degree",
            "result_capacity",
            "use_soa",
            "max_nfa_size",
            "use_uvm",
            "unique_frequency",
            "input_len",
            "precompute_cutoff",
            "precompute_depth",
            "algorithm",
            "group_num",
            "add_aas_interval",
            "remove_degree",
            "add_aan_start",
            "active_threshold",
            "duplicate_input_stream",
            "unique",
            "pc_use_uvm",
            "input",
            "isHS",
            "isVASim",
            "app_name",
            "validation",
            "no_name_provided",
            "quick_validation"]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    #TODO look at the output
    # https://github.com/getianao/ngAP
    @staticmethod
    def _parse_results(
        output: str,
        run_variables: Dict[str, Any]
    ) -> Dict[str, str]:

        names = run_variables.keys()
        values = run_variables.values()
        result_dict = dict(zip(names, values))

        lines = output.splitlines()
        for line_idx in range(len(lines)):
            line = lines[line_idx]
            if "Result" in line:
                result_line = lines[line_idx+1]
                result_values = result_line.split()
                result_values_stripped = [v.strip(',') for v in result_values]
                for rvs_idx in range(len(result_values_stripped)):
                    rvs = result_values_stripped[rvs_idx]
                    result_dict[f"Result_{rvs_idx}"] = rvs

            if "Reference result" in line:
                ref_line = lines[line_idx+1]
                ref_values = ref_line.split()
                ref_values_stripped = [v.strip(',') for v in ref_values]
                for rvs_idx in range(len(ref_values_stripped)):
                    rvs = ref_values_stripped[rvs_idx]
                    result_dict[f"Ref_Result_{rvs_idx}"] = rvs

            if "ngap elapsed time" in line:
                measurements = line.split(',')

                time = measurements[0].split(':')[1]
                time_val_and_unit = time.split()
                time_val = time_val_and_unit[0]
                time_unit = time_val_and_unit[1]
                result_dict[f"time {time_unit}"] = time_val

                throughput = measurements[1].split('=')[1]
                throughput_val_and_unit = throughput.split()
                throughput_val = throughput_val_and_unit[0]
                throughput_unit = throughput_val_and_unit[1]
                result_dict[f"throughput {throughput_unit}"] = throughput_val

        return result_dict

    # TODO probably mention ngAP here
    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + []

    def build_tilt(self, **kwargs) -> None:
        self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs):
        pass

    # def prebuild_bench(self, **_kwargs) -> None:
    #     build_dir = self._build_dir
    #     self.platform.comm.makedirs(path=build_dir, exist_ok=True)

    #     must_debug = self.must_debug()
    #     cmake_build_type = "Debug" if must_debug else "Release"

    #     self.platform.comm.shell(
    #         command=f"cmake -DCMAKE_BUILD_TYPE={cmake_build_type} {self._bench_src_path}",
    #         current_dir=build_dir,
    #         output_is_log=True,
    #     )
    #     self.platform.comm.shell(
    #         command=f"make{self._parallel_make_str()} db_bench",
    #         current_dir=build_dir,
    #         output_is_log=True,
    #     )
    #     if not self.platform.comm.isdir(self._tmpdb_dir):
    #         self.platform.comm.makedirs(path=self._tmpdb_dir, exist_ok=True)
    #         db_init_command = [
    #             "./db_bench",
    #             "--threads=1",
    #             "--benchmarks=fillseq",
    #             f"--db={self._tmpdb_dir}",
    #         ]
    #         self.platform.comm.shell(command=db_init_command, current_dir=build_dir)

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    """
    ngap -a ${NGAP_ROOT}/small_dataset/apple.anml                                         \
    -i ${NGAP_ROOT}/small_dataset/inputstream.txt                                       \
    --app-name=apple --algorithm=nonblockingallgroups --input-start-pos=0               \
    --input-len=81 --split-entire-inputstream-to-chunk-size=81  --group-num=1           \
    --duplicate-input-stream=1 --unique=false --unique-frequency=10 --use-soa=false     \
    --result-capacity=54619400 --use-uvm=false --data-buffer-fetch-size=25600000        \
    --add-aan-start=256 --add-aas-interval=32 --active-threshold=10                     \
    --precompute-cutoff=-1 --precompute-depth=3 --compress-prec-table=true              \
    --report-off=false --validation=true
    """

    def single_run(  # pylint: disable=arguments-differ
        input_start_pos,
        report_off,
        split_entire_inputstream_to_chunk_size,
        compress_prec_table,
        data_buffer_fetch_size,
        quit_degree,
        result_capacity,
        use_soa,
        max_nfa_size,
        use_uvm,
        unique_frequency,
        input_len,
        precompute_cutoff,
        precompute_depth,
        algorithm,
        group_num,
        add_aas_interval,
        remove_degree,
        add_aan_start,
        active_threshold,
        duplicate_input_stream,
        unique,
        pc_use_uvm,
        input,
        automata,
        isHS,
        isVASim,
        app_name,
        quick_validation,
        enable_validation,
        output_file,
        **kwargs,
    ) -> str:

        command = [
            "ngap",
            "-a",
            f"{automata}",
            "-i",
            f"{input}",
            f"--app-name={app_name}"]

        if algorithm is not None: command.extend([f"--algorithm={algorithm}"])
        if input_start_pos is not None: command.extend([f"--input-start-pos={input_start_pos}"])
        if input_len is not None: command.extend([f"--input-len={input_len}"])
        if split_entire_inputstream_to_chunk_size is not None: command.extend([f"--split-entire-inputstream-to-chunk-size={split_to_chunk_size}"])
        if group_num is not None: command.extend([f"--input-len={input_len}"])
        if duplicate_input_stream is not None: command.extend([f"--input-len={input_len}"])
        if unique is not None: command.extend([f"--unique={unique}"])
        if unique_frequency is not None: command.extend([f"--unique-frequency={unique_frequency}"])
        if use_soa is not None: command.extend([f"--use_soa={use_soa}"])
        if result_capacity is not None: command.extend([f"--result_capacity={result_capacity}"])
        if use_uvm is not None: command.extend([f"--use_uvm={use_uvm}"])
        if data_buffer_fetch_size: command.extend([f"--data_buffer_fetch_size={data_buffer_fetch_size}"]) 
        if add_aan_start: command.extend([f"--add_aan_start={add_aan_start}"]) 
        if add_aas_interval: command.extend([f"--add_aas_interval={add_aas_interval}"]) 
        if active_threshold: command.extend([f"--active_threshold={active_threshold}"]) 
        if precompute_cutoff: command.extend([f"--precompute_cutoff={precompute_cutoff}"]) 
        if precompute_depth: command.extend([f"--precompute_depth={precompute_depth}"]) 
        if compress_prec_table: command.extend([f"--compress_prec_table={compress_prec_table}"]) 
        if pc_use_uvm: command.extend([f"--pc_use_uvm={pc_use_uvm}"]) 
        if report_off: command.extend([f"--report_off={report_off}"]) 
        if remove_degree: command.extend([f"--remove_degree={remove_degree}"]) 
        if quit_degree: command.extend([f"--quit_degree={quit_degree}"]) 
        if max_nfa_size: command.extend([f"--max_nfa_size={max_nfa_size}"]) 

        if isHS:
            command.extend(["--support"])
            if quick_validation is not None:
                command.extend([f"-v {quick_validation}"])
        elif isVASim:
            command.extend(["-t"])
        else:
            command.extend([f"--validation={enable_validation}"])
            if quick_validation is not None:
                command.extend([f"--quick-validation={quick_validation}"])


        environment = self._preload_env(
            input_start_pos,
            report_off,
            split_entire_inputstream_to_chunk_size,
            compress_prec_table,
            data_buffer_fetch_size,
            quit_degree,
            result_capacity,
            use_soa,
            max_nfa_size,
            use_uvm,
            unique_frequency,
            input_len,
            precompute_cutoff,
            precompute_depth,
            algorithm,
            group_num,
            add_aas_interval,
            remove_degree,
            add_aan_start,
            active_threshold,
            duplicate_input_stream,
            unique,
            pc_use_uvm,
            input,
            automata,
            isHS,
            isVASim,
            app_name,
            quick_validation,
            enable_validation,
            output_file,
            kwargs**)


        if bench_name in ["readrandom", "readmissing", "readhot", "seekrandom"]:
            duration_num = f"--duration={benchmark_duration_seconds}"
        else:
            duration_num = f"--num={num // nb_threads}"

        if bench_name in [
            "fillseq",
            "fillrandom",
            "fillsync",
            "fill100K",
        ]:
            use_existing_db = False
        else:
            use_existing_db = True

        run_command = [
            "./db_bench",
            f"--threads={nb_threads}",
            f"--benchmarks={bench_name}",
            f'--use_existing_db={"1" if use_existing_db else "0"}',
            f"--db={self._tmpdb_dir}",
            duration_num,
        ]
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            cpu_order=cpu_order,
            master_thread_core=master_thread_core,
            nb_threads=nb_threads,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            current_dir=self._build_dir,
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

        result_dict = self._parse_results(command_output, run_variables)
        return result_dict


def ngap_breakdown_campaign(
    benchmark: Benchmark,
    variables: Dict[str, Iterable[Any]],
    name: str = None,
    nb_runs: int = 1,
    constants: Constants = None,
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    benchmark_duration_seconds: Optional[int] = None,
    results_dir: Optional[PathType] = None,
) -> CampaignIterateVariables:
    
    return CampaignIterateVariables(
        name = name,
        benchmark = benchmark,
        nb_runs = nb_runs,
        variables = variables,
        constants = constants,
        debug = debug,
        gdb = gdb,
        enable_data_dir = enable_data_dir,
        continuing = continuing,
        benchmark_duration_seconds = benchmark_duration_seconds,
        results_dir = results_dir
    )


def main():

    ncu_wrapper = NcuWrap(set="full")
    benchmark = BreakdownBench(
        command_attachments=ncu_wrapper,
        post_run_hooks=[ncu_wrapper.post_run_hook_update_results])

    # parse the config and app files
    app_file = "./app_spec_ngap_new_quickvalidation_part1"
    config_file = "./exec_config_ngap_groups_design_NAP"
    vars_part1 = gen_dict_list(app_file, config_file)
    part1_campaign = ngap_breakdown_campaign(
        name = "Part1_Breakdown", 
        variables=vars_part1,
        benchmark=benchmark)

    app_file_2 = "./app_spec_ngap_new_quickvalidation_part1"
    config_file_2 = "./exec_config_ngap_groups_design_NAP"
    vars_part2 = gen_dict_list(app_file_2, config_file_2)
    part2_campaign = ngap_breakdown_campaign(
        name = "Part2_Breakdown", 
        variables=vars_part2,
        benchmark=benchmark)

    app_file_3 = "./app_spec_ngap_new_quickvalidation_part1"
    config_file_3 = "./exec_config_ngap_groups_design_NAP"
    vars_part3 = gen_dict_list(app_file_3, config_file_3)
    part3_campaign = ngap_breakdown_campaign(
        name = "Part3_Breakdown", 
        variables=vars_part3,
        benchmark=benchmark)


if __name__ == '__main__':
    pass