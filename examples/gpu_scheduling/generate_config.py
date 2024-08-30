#!/bin/python3

import json
import random

def first_el(mytup, index):
    if type(mytup) is tuple:
        return mytup[index]
    return mytup

def generate_benchmark(index, config_dict, output_folder):
    number = index + 1
    kernel_config_string = ""
    kernel_config_list = []

    benchmark = {}
    benchmark["filename"] = "./bin/" + config_dict.get("kernel_names", None) + ".so"
    benchmark["log_name"] = f"./{output_folder}/output_{number}.json"
    benchmark["label"] = f"Kernel {number}"
    benchmark["thread_count"] = config_dict.get("cthread_counts", 32)
    benchmark["block_count"] = config_dict.get("block_counts", 32)
    benchmark["data_size"] = config_dict.get("data_sizes", 0)
    benchmark["additional_info"] = config_dict.get("additional_infos", None)
    benchmark["sm_mask"] = config_dict.get("sm_masks", None)
    benchmark["release_time"] = config_dict.get("release_times", None)
    return {k: v for k, v in benchmark.items() if v is not None}

def generate_config(config_dict, output_folder):

    # Generate individual benchmark configs
    benchmarks = []
    for i in range(len(config_dict["kernel_names"])):
        indexed_config_dict = {k: (lambda x: first_el(x, i))(v) for k, v in config_dict.items()}
        benchmark = generate_benchmark(i, indexed_config_dict, output_folder)
        benchmarks.append(benchmark)

    # Generate the top-level global config
    config = {}
    config["name"] = "benchkit-benchmarks"
    config["max_iterations"] = config_dict.get("iterations", 1)
    config["max_time"] = config_dict.get("max_time", 0)
    config["cuda_device"] = config_dict.get("cuda_device", 0)
    config["pin_cpus"] = config_dict.get("pin_cpus", False)
    config["benchmarks"] = benchmarks
    return json.dumps(config, indent=2)
