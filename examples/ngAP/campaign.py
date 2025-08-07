import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignIterateVariables, Constants, CampaignSuite
from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import PathType
from benchkit.commandwrappers.ncu import NcuWrap, CommandWrapper

from parse_options import gen_dict_list, possible_vars

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

        output = self.run_bench_command(
            run_command=command,
            wrapped_run_command=wrapped_command,
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


def check_dicts(list_of_dicts):
    for d in list_of_dicts:
        for key in possible_vars:
            if key not in d:
                return False

    return True


def ngap_campaign(
    app_file: str,
    config_file: str,
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

    ncu_wrapper = NcuWrap(user_set="full")
    benchmark = NgapBench(
        command_wrappers=[ncu_wrapper],
        post_run_hooks=[ncu_wrapper.post_run_hook_update_results])

    vars = gen_dict_list(app_file, config_file)
    assert(check_dicts(vars))
    
    return CampaignIterateVariables(
        name = name,
        benchmark = benchmark,
        nb_runs = nb_runs,
        variables = vars,
        constants = constants,
        debug = debug,
        gdb = gdb,
        enable_data_dir = enable_data_dir,
        continuing = continuing,
        benchmark_duration_seconds = benchmark_duration_seconds,
        results_dir = results_dir
    )


def get_breakdown_configs():
    return [
        ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_NAP"),
        ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_NAP"),
        ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_NAP_4degree")
    ]

def get_sensitivity_configs():
    return [
        ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_sota_oneinput"),
        ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_best_oneinput"),
        ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_sota_runahead_oneinput"),
        ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_nap_default_oneinput"),

        ("./configs/app_spec_ngap_new_quickvalidation_part2","./configs/exec_config_ngap_groups_best_oneinput"),
        ("./configs/app_spec_ngap_new_quickvalidation_part2","./configs/exec_config_ngap_groups_design_sota_runahead_oneinput"),
        ("./configs/app_spec_ngap_new_quickvalidation_part2","./configs/exec_config_ngap_groups_nap_default_oneinput"),

        ("./configs/app_spec_ngap_new_quickvalidation_part3","./configs/exec_config_ngap_groups_best_4degree_oneinput"),
        ("./configs/app_spec_ngap_new_quickvalidation_part3","./configs/exec_config_ngap_groups_design_sota_4degree_oneinput"),
        ("./configs/app_spec_ngap_new_quickvalidation_part3","./configs/exec_config_ngap_groups_nap_default_4degree_oneinput"),
        ("./configs/app_spec_ngap_new_quickvalidation_part3","./configs/exec_config_ngap_groups_design_sota_runahead_4degree_oneinput"),

        ("./configs/app_spec_ngap_new_quickvalidation_part1","./configs/exec_config_ngap_groups_design_cpu_oneinput"),
        ("./configs/app_spec_ngap_new_quickvalidation_part2","./configs/exec_config_ngap_groups_design_cpu_oneinput"),
    ]



def main():

    # Breakdown Benchmarks

    breakdown_configs = get_breakdown_configs()
    breakdown_campaigns = []
    for app, config in breakdown_configs:
        breakdown_campaigns.append(ngap_campaign(app_file=app,
                                                 config_file=config,
                                                 name=f"Breakdown_{app}_{config}"))

    campaign_suite = CampaignSuite(campaigns=breakdown_campaigns)
    campaign_suite.print_durations()
    campaign_suite.run_suite()

    # Sensitivity Benchmarks

    sensitivity_configs = get_sensitivity_configs()
    sensitivity_campaigns = []
    for app, config in sensitivity_configs:
        sensitivity_campaigns.append(ngap_campaign(app_file=app,
                                                 config_file=config,
                                                 name=f"Sensitivity_{app}_{config}"))

    campaign_suite = CampaignSuite(campaigns=sensitivity_campaigns)
    campaign_suite.print_durations()
    campaign_suite.run_suite()

if __name__ == '__main__':
    main()
