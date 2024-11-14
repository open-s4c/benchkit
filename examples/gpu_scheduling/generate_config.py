#!/bin/python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import json


def first_el(mytuple, index):
    if type(mytuple) is tuple:
        return mytuple[index]
    return mytuple


def generate_benchmark(index, config_dict, output_folder):
    number = index + 1

    benchmark = {
        "filename": "./bin/" + config_dict.get("kernel_names", None) + ".so",
        "log_name": f"./{output_folder}/output_{number}.json",
        "label": f"Kernel {number}",
        "thread_count": config_dict.get("cthread_counts", 32),
        "block_count": config_dict.get("block_counts", 32),
        "data_size": config_dict.get("data_sizes", 0),
        "additional_info": config_dict.get("additional_infos", None),
        "sm_mask": config_dict.get("sm_masks", None),
        "release_time": config_dict.get("release_times", None),
    }
    return {k: v for k, v in benchmark.items() if v is not None}


def generate_config(config_dict, output_folder):

    # Generate individual benchmark configs
    benchmarks = []
    for i in range(len(config_dict["kernel_names"])):
        indexed_config_dict = {k: (lambda x: first_el(x, i))(v) for k, v in config_dict.items()}
        benchmark = generate_benchmark(i, indexed_config_dict, output_folder)
        benchmarks.append(benchmark)

    # Generate the top-level global config
    config = {
        "name": "benchkit-benchmarks",
        "max_iterations": config_dict.get("iterations", 1),
        "max_time": config_dict.get("max_time", 0),
        "cuda_device": config_dict.get("cuda_device", 0),
        "pin_cpus": config_dict.get("pin_cpus", False),
        "benchmarks": benchmarks,
    }
    return json.dumps(config, indent=2)
