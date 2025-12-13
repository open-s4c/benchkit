# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import re
from abc import ABC, abstractmethod
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.dependencies.packages import PackageDependency
from benchkit.shell.shell import shell_out
from benchkit.utils.types import PathType


class LibbpfTools(ABC):

    @abstractmethod
    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        pass

    @abstractmethod
    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> RecordResult:
        pass

    def dependencies(self) -> List[PackageDependency]:
        """Dependencies of the command wrapper.

        Returns:
            List[PackageDependency]: list of dependencies.
        """

        distribution_name_re = re.compile(r"^NAME=\"(\S+)\"$")
        distribution_version_re = re.compile(r"^VERSION_ID=\"(\d+.\d+)\"$")

        out = shell_out("cat /etc/os-release", print_input=False, print_output=False)

        name = ""
        version = ""
        for line in out.split("\n"):
            name_match = distribution_name_re.search(line)
            version_match = distribution_version_re.search(line)

            if name_match:
                name = name_match.group(1)
            if version_match:
                version = version_match.group(1)

        if name != "Ubuntu":
            print(f"Klockstat: unkown dependencies for {name}")
            return []

        default_deps = [
            PackageDependency("zip"),
            PackageDependency("bison"),
            PackageDependency("build-essential"),
            PackageDependency("cmake"),
            PackageDependency("flex"),
            PackageDependency("git"),
            PackageDependency("libedit-dev"),
            PackageDependency("zlib1g-dev"),
            PackageDependency("libelf-dev"),
            PackageDependency("liblzma-dev"),
            PackageDependency("python3-setuptools"),
            PackageDependency("libfl-dev"),
            PackageDependency("arping"),
            PackageDependency("netperf"),
            PackageDependency("iperf"),
        ]

        deps_dict: dict[str, List[PackageDependency]] = {}
        deps_dict["20.04.1"] = default_deps + [
            PackageDependency("libllvm12"),
            PackageDependency("llvm-12-dev"),
            PackageDependency("libclang-12-dev"),
            PackageDependency("python"),
        ]

        deps_dict["21.04"] = default_deps + [
            PackageDependency("libllvm12"),
            PackageDependency("llvm-12-dev"),
            PackageDependency("libclang-12-dev"),
            PackageDependency("python3"),
        ]

        deps_dict["21.10"] = default_deps + [
            PackageDependency("libllvm12"),
            PackageDependency("llvm-12-dev"),
            PackageDependency("libclang-12-dev"),
            PackageDependency("python3"),
        ]

        deps_dict["23.04"] = default_deps + [
            PackageDependency("libllvm15"),
            PackageDependency("llvm-15-dev"),
            PackageDependency("libclang-15-dev"),
            PackageDependency("python3"),
            PackageDependency("libdebuginfod-dev"),
            PackageDependency("libpolly-15-dev"),
        ]

        deps_dict["23.10"] = default_deps + [
            PackageDependency("libllvm16"),
            PackageDependency("llvm-16-dev"),
            PackageDependency("libclang-16-dev"),
            PackageDependency("python3"),
            PackageDependency("libdebuginfod-dev"),
            PackageDependency("libpolly-16-dev"),
        ]

        deps_dict["24.04"] = default_deps + [
            PackageDependency("libllvm18"),
            PackageDependency("llvm-18-dev"),
            PackageDependency("libclang-18-dev"),
            PackageDependency("python3"),
            PackageDependency("libdebuginfod-dev"),
            PackageDependency("libpolly-18-dev"),
        ]

        return deps_dict.get(
            version,
            default_deps
            + [
                PackageDependency("libllvm3.7"),
                PackageDependency("llvm-3.7-dev"),
                PackageDependency("libclang-3.7-dev"),
                PackageDependency("python"),
            ],
        )
