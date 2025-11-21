import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignIterateVariables, Constants, CampaignSuite
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType
from benchkit.commandwrappers.ncu2 import NcuWrap, CommandWrapper
from benchkit.platforms import get_current_platform


from parse_options import gen_dict_list, possible_vars
import subprocess


class NgapBench(Benchmark):
    def __init__(
        self,
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

        self._bench_src_path = "/ngAP"
        self._build_dir = self.bench_src_path + "/code/build"

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            'active_threshold', 
            'adaptive_aas', 
            'add_aan_start', 
            'add_aas_interval', 
            'algorithm', 
            'app_name', 
            'automata', 
            'block_size', 
            'compress_prec_table', 
            'data_buffer_fetch_size', 
            'duplicate_input_stream', 
            'group_num', 
            'input', 
            'input_len', 
            'input_start_pos', 
            'isHS', 
            'isVASim', 
            'max_nfa_size', 
            'motivate_worklist_length', 
            'num_state_per_group', 
            'only_exec_cc_with_state_id', 
            'only_exec_ccid', 
            'output_file', 
            'padding', 
            'pc_use_uvm', 
            'precompute_cutoff', 
            'precompute_depth', 
            'quick_validation', 
            'quit_degree', 
            'remove_degree', 
            'report_filename', 
            'report_off', 
            'result_capacity', 
            'split_entire_inputstream_to_chunk_size', 
            'try_adaptive_aas', 
            'tuning', 
            'unique', 
            'unique_frequency', 
            'use_soa', 
            'use_uvm', 
            'validation']

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

            # ncu output
            if line.startswith("==PROF=="):
                continue

            if line.startswith("read input steam from file = "):
                is_file = line.split(" = ")[1]
                result_dict["input_stream"] = is_file

            if line.startswith("load automata from file = "):
                at_file = line.split(" = ")[1]
                result_dict["automata_file"] = at_file

            if line.startswith("input_stream_size = "):
                is_size = line.split(" = ")[1]
                result_dict["input_stream_size"] = is_size

            # NFA info
            if "total_state_number" in line:
                val = line.split(" = ")[1]
                result_dict["total state numb"] = val
            if "start_state_number" in line: 
                val = line.split(" = ")[1]
                result_dict["start state numb"] = val
            if "always_active_state_number" in line:
                val = line.split(" = ")[1]
                result_dict["aa state num"] = val
            if "report_state_number" in line:
                val = line.split(" = ")[1]
                result_dict["report state num"] = val
            if "total_cc_number" in line:
                val = line.split(" = ")[1]
                result_dict["total cc num"] = val
            if "cc_256_number" in line:
                val = line.split(" = ")[1]
                result_dict["cc 256 num"] = val
            if "max_cc_size" in line:
                val = line.split(" = ")[1]
                result_dict["max cc size"] = val
            if "average_cc_size" in line:
                val = line.split(" = ")[1]
                result_dict["avg cc size"] = val

            # Input steam info
            if "input_start_pos" in line:
                val = line.split(" = ")[1]
                result_dict["input start pos"] = val
            if "input_length" in line:
                val = line.split(" = ")[1]
                result_dict["input length"] = val
            if "split_entire_inputstream_to_chunk_size" in line:
                val = line.split(" = ")[1]
                result_dict["chunk size"] = val
            if "dup_input_stream" in line:
                val = line.split(" = ")[1]
                result_dict["duplicate"] = val

            if "Result " in line:
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
        self,
        active_threshold, 
        adaptive_aas, 
        add_aan_start, 
        add_aas_interval, 
        algorithm, 
        app_name, 
        automata, 
        block_size, 
        compress_prec_table, 
        data_buffer_fetch_size, 
        duplicate_input_stream, 
        group_num, 
        input, 
        input_len, 
        input_start_pos, 
        isHS, 
        isVASim, 
        max_nfa_size, 
        motivate_worklist_length, 
        num_state_per_group, 
        only_exec_cc_with_state_id, 
        only_exec_ccid, 
        output_file, 
        padding, 
        pc_use_uvm, 
        precompute_cutoff, 
        precompute_depth, 
        quick_validation, 
        quit_degree, 
        remove_degree, 
        report_filename, 
        report_off, 
        result_capacity, 
        split_entire_inputstream_to_chunk_size, 
        try_adaptive_aas, 
        tuning, 
        unique, 
        unique_frequency, 
        use_soa, 
        use_uvm, 
        validation,
        **kwargs,
    ) -> str:

        command = [
            "ngap",
            f"--automata={automata}",
            f"--input={input}",
            f"--app-name={app_name}"]

        if algorithm is not None: command.extend([f"--algorithm={algorithm}"])
        if input_start_pos is not None: command.extend([f"--input-start-pos={input_start_pos}"])
        if input_len is not None: command.extend([f"--input-len={input_len}"])
        if split_entire_inputstream_to_chunk_size is not None:
            command.extend([f"--split-entire-inputstream-to-chunk-size={split_entire_inputstream_to_chunk_size}"])
        if group_num is not None: command.extend([f"--group-num={group_num}"])
        if duplicate_input_stream is not None:
            command.extend([f"--duplicate-input-stream={duplicate_input_stream}"])
        if unique is not None: command.extend([f"--unique={unique}"])
        if unique_frequency is not None: command.extend([f"--unique-frequency={unique_frequency}"])
        if use_soa is not None: command.extend([f"--use-soa={use_soa}"])
        if result_capacity is not None: command.extend([f"--result-capacity={result_capacity}"])
        if use_uvm is not None: command.extend([f"--use-uvm={use_uvm}"])
        if data_buffer_fetch_size is not None: command.extend([f"--data-buffer-fetch-size={data_buffer_fetch_size}"]) 
        if add_aan_start is not None: command.extend([f"--add-aan-start={add_aan_start}"]) 
        if add_aas_interval is not None: command.extend([f"--add-aas-interval={add_aas_interval}"]) 
        if active_threshold is not None: command.extend([f"--active-threshold={active_threshold}"]) 
        if precompute_cutoff is not None: command.extend([f"--precompute-cutoff={precompute_cutoff}"]) 
        if precompute_depth is not None: command.extend([f"--precompute-depth={precompute_depth}"]) 
        if compress_prec_table is not None: command.extend([f"--compress-prec-table={compress_prec_table}"]) 
        if pc_use_uvm is not None: command.extend([f"--pc-use-uvm={pc_use_uvm}"]) 
        if report_off is not None: command.extend([f"--report-off={report_off}"]) 
        if remove_degree is not None: command.extend([f"--remove-degree={remove_degree}"]) 
        if quit_degree is not None: command.extend([f"--quit-degree={quit_degree}"]) 
        if max_nfa_size is not None: command.extend([f"--max-nfa-size={max_nfa_size}"]) 

        if adaptive_aas is not None: command.extend([f"--adaptive-aas={adaptive_aas}"])
        if block_size is not None: command.extend([f"--block-size={block_size}"])
        if motivate_worklist_length is not None: command.extend([f"--motivate-worklist-length={motivate_worklist_length}"])
        if num_state_per_group is not None: command.extend([f"--num-state-per-group={num_state_per_group}"])
        if only_exec_cc_with_state_id is not None: command.extend([f"--only-exec-cc-with-state-id={only_exec_cc_with_state_id}"])
        if only_exec_ccid is not None: command.extend([f"--only-exec-ccid={only_exec_ccid}"])
        if output_file is not None: command.extend([f"--output-file={output_file}"])
        if padding is not None: command.extend([f"--padding={padding}"])
        if report_filename is not None: command.extend([f"--report-filename={report_filename}"])
        if try_adaptive_aas is not None: command.extend([f"--try-adaptive-aas={try_adaptive_aas}"])
        if tuning is not None: command.extend([f"--tuning={tuning}"])

        if isHS:
            command.extend(["--support"])
            if quick_validation is not None:
                command.extend([f"-v {quick_validation}"])
        elif isVASim:
            command.extend(["-t"])
        else:
            command.extend([f"--validation={validation}"])
            if quick_validation is not None:
                command.extend([f"--quick-validation={quick_validation}"])


        environment = self._preload_env(**kwargs)

        wrapped_command, wrapped_environment = self._wrap_command(
            run_command=command,
            environment=environment,
            **kwargs,
        )

        try:
            output = self.run_bench_command(
                run_command=command,
                wrapped_run_command=wrapped_command,
                current_dir=self._build_dir,
                environment=environment,
                wrapped_environment=wrapped_environment,
                print_output=True,
                timeout=3600,
                ignore_any_error_code=True)
            return output
        except subprocess.TimeoutExpired:
            return ""
        


    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str | None,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:

        if command_output is "":
            # output_dict = possible_vars.copy()
            # output_dict["input_stream"] = None
            # output_dict["automata_file"] = None
            # output_dict["input_stream_size"] = None
            # output_dict["total state numb"] = None
            # output_dict["start state numb"] = None
            # output_dict["aa state num"] = None
            # output_dict["report state num"] = None
            # output_dict["total cc num"] = None
            # output_dict["cc 256 num"] = None
            # output_dict["max cc size"] = None
            # output_dict["avg cc size"] = None
            # output_dict["input start pos"] = None
            # output_dict["input length"] = None
            # output_dict["chunk size"] = None
            # output_dict["duplicate"] = None
            # output_dict[f"time"] = None
            # output_dict[f"throughput"] = None
            return {}

        result_dict = self._parse_results(command_output, run_variables)
        return result_dict


def check_dicts(list_of_dicts):
    for d in list_of_dicts:
        for key in possible_vars:
            if key not in d:
                return False

    return True


def ngap_campaign(
    app_file: str,
    config_file: str,
    name_prefix: str = None,
    nb_runs: int = 1,
    constants: Constants = None,
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    benchmark_duration_seconds: Optional[int] = None,
    # results_dir: Optional[PathType] = None,
) -> CampaignIterateVariables:

    platform = get_current_platform()
    # ncu_wrapper = NcuWrap(user_set="full")

    ncu_wrapper = NcuWrap(metrics=metric_list,force_overwrite=True,report_or_log=True,csv=True)
    benchmark = NgapBench(
        command_wrappers=[ncu_wrapper],
        post_run_hooks=[ncu_wrapper.post_run_hook_update_results],
        platform=platform)
    # benchmark = NgapBench(platform=platform)

    vars = gen_dict_list(app_file, config_file)
    assert(check_dicts(vars))

    part = app_file.split("_")[-1]
    con = config_file.split("./configs/exec_config_ngap_groups_")[1]
    
    return CampaignIterateVariables(
        name = f"{name_prefix}_{part}_{con}",
        benchmark = benchmark,
        nb_runs = nb_runs,
        variables = vars,
        constants = constants,
        debug = debug,
        gdb = gdb,
        enable_data_dir = enable_data_dir,
        continuing = continuing,
        benchmark_duration_seconds = benchmark_duration_seconds,
        # results_dir = results_dir
    )


def get_breakdown_configs():
    return [
        ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_NAP"),
        ("./configs/app_spec_ngap_new_quickvalidation_part2","./configs/exec_config_ngap_groups_design_NAP"),
        ("./configs/app_spec_ngap_new_quickvalidation_part3","./configs/exec_config_ngap_groups_design_NAP_4degree")
    ]

# def get_sensitivity_configs():
#     return [
#         ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_sota_oneinput"),
#         ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_best_oneinput"),
#         ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_sota_runahead_oneinput"),
#         ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_nap_default_oneinput"),

#         ("./configs/app_spec_ngap_new_quickvalidation_part2","./configs/exec_config_ngap_groups_best_oneinput"),
#         ("./configs/app_spec_ngap_new_quickvalidation_part2","./configs/exec_config_ngap_groups_design_sota_runahead_oneinput"),
#         ("./configs/app_spec_ngap_new_quickvalidation_part2","./configs/exec_config_ngap_groups_nap_default_oneinput"),

#         ("./configs/app_spec_ngap_new_quickvalidation_part3","./configs/exec_config_ngap_groups_best_4degree_oneinput"),
#         ("./configs/app_spec_ngap_new_quickvalidation_part3","./configs/exec_config_ngap_groups_design_sota_4degree_oneinput"),
#         ("./configs/app_spec_ngap_new_quickvalidation_part3","./configs/exec_config_ngap_groups_nap_default_4degree_oneinput"),
#         ("./configs/app_spec_ngap_new_quickvalidation_part3","./configs/exec_config_ngap_groups_design_sota_runahead_4degree_oneinput"),

#         ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_cpu_oneinput"),
#         ("./configs/app_spec_ngap_new_quickvalidation_part2","./configs/exec_config_ngap_groups_design_cpu_oneinput"),
#     ]


metric_list = [
    # "group:memory__first_level_cache_table",
    # "sass__inst_executed_global_loads",
    # "sass__inst_executed_global_stores",
    # of bytes written to L2 for global atomics
    # "l1tex__m_l1tex2xbar_write_bytes_mem_global_op_atom",
    # of bytes read from L2 into L1TEX M-Stage for global atomics
    # "l1tex__m_xbar2l1tex_read_bytes_mem_global_op_atom",
    # of bytes requested for global atomics
    # "l1tex__t_bytes_pipe_lsu_mem_global_op_atom",
    # of bytes requested that missed for global atomics
    # "l1tex__t_bytes_pipe_lsu_mem_global_op_atom_lookup_miss",
    #    SM throughput assuming ideal load balancing across SMSPs
    # "sm__throughput.avg.pct_of_peak_sustained_active",
    # proportion of warps per cycle, waiting for sibling warps at a CTA
    # "smsp__warp_issue_stalled_barrier_per_warp_active.pct",
    # proportion of warps per cycle, waiting on a memory barrier
    # "smsp__warp_issue_stalled_membar_per_warp_active.pct",
    # cumulative # of warps in flight
    # "sm__warps_active.avg.pct_of_peak_sustained_active",
    # "sm__maximum_warps_per_active_cycle_pct",
    # of cycles where local/global/shared writeback interface was active
    # "l1tex__lsu_writeback_active.avg.pct_of_peak_sustained_active",
    # of sector hits per sector
    "l1tex__t_sector_hit_rate",  # L1/TEX hit rate
    # proportion of L2 sector lookups that hit
    "lts__t_sector_hit_rate", # L2 hit rate
    # average # of active threads per instruction executed
    "smsp__thread_inst_executed_per_inst_executed",
    # of bytes accessed in DRAM
    # "dram__bytes",
    # # of bytes read from DRAM                            
    "dram__bytes_read",
    # # of bytes written to DRAM
    "dram__bytes_write",
]

def main():

    # Breakdown Benchmarks
    breakdown_configs = get_breakdown_configs()
    breakdown_campaigns = []
    for app, config in breakdown_configs:
        breakdown_campaigns.append(ngap_campaign(app_file=app,
                                                 config_file=config,
                                                 name_prefix="breakdown",
                                                 enable_data_dir=True))

    campaign_suite = CampaignSuite(campaigns=breakdown_campaigns)
    campaign_suite.print_durations()
    campaign_suite.run_suite()


    # Sensitivity Benchmarks
    # sensitivity_configs = get_sensitivity_configs()
    # sensitivity_campaigns = []
    # for app, config in sensitivity_configs:
    #     sensitivity_campaigns.append(ngap_campaign(app_file=app,
    #                                                config_file=config,
    #                                                name_prefix="sensitivity"))

    # campaign_suite = CampaignSuite(campaigns=sensitivity_campaigns)
    # campaign_suite.print_durations()
    # campaign_suite.run_suite()

if __name__ == '__main__':
    main()
