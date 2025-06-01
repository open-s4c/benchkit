# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT
import re
from typing import Any, Dict, List

def parse_output(output: str) -> Dict[str, Any]:
	lines = output.strip().splitlines()

	# Extract number of cores
	cores_match = re.search(r'\[(\d+)\s+cores\]', lines[0])
	cores = int(cores_match.group(1)) if cores_match else None
	
	# Extract runtime key-value pairs
	runtime_in_ms = {}
	for match in re.finditer(r'(\w+):\s+(\d+)', lines[1]):
		key, value = match.groups()
		runtime_in_ms[key.lower()] = int(value)

	
	# Extract number of tasks
	num_tasks = {
		key.lower(): int(value)
		for key, value in re.findall(r'(\w+):\s+(\d+)', lines[3])
	}

	return {
		"number_of_cores": cores,
		"runtime_in_ms": runtime_in_ms,
		"number_of_tasks": num_tasks
	}

def parse_outputs(output: str, output_keys: List[str]) -> Dict[str, any]:
	result_dict = {}
	blocks = re.split(r'(?=Runtime in millisecond \[\d+ cores\])', output.strip())
	
	for i, block in enumerate(blocks[1:]):
		if i >= len(output_keys):
			break  # Ignore extra blocks if no key is provided

		lines = block.strip().splitlines()
		if len(lines) < 4:
			continue  # Skip incomplete blocks

		# Extract cores
		cores_match = re.search(r'\[(\d+)\s+cores\]', lines[0])
		cores = int(cores_match.group(1)) if cores_match else None

		# Extract runtime values
		runtime_in_ms = {
			key.lower(): int(value)
			for key, value in re.findall(r'(\w+):\s+(\d+)', lines[1])
		}

		# Extract number of tasks
		num_tasks = {
			key.lower(): int(value)
			for key, value in re.findall(r'(\w+):\s+(\d+)', lines[3])
		}

		result_dict[output_keys[i]] = {
			"number_of_cores": cores,
			"runtime_in_ms": runtime_in_ms,
			"number_of_tasks": num_tasks
		}

	return result_dict
