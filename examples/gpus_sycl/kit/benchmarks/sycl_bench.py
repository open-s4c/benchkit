import csv
import pathlib
import re
from typing import Any, Dict, List

from benchkit.benchmark import Benchmark
from benchkit.platforms import Platform
from benchkit.utils.types import PathType


class SyclBench(Benchmark):
    def __init__(
        self,
        platform: Platform,
        src_dir: PathType,
        build_dir: PathType,
        cmake_target: str,
        command_attachments=(),
    ) -> None:
        super().__init__(
            command_wrappers=(),
            command_attachments=command_attachments,
            shared_libs=(),
            pre_run_hooks=(),
            post_run_hooks=(),
        )
        self.platform = platform
        self._cmake_target = cmake_target
        self._bench_src_path = pathlib.Path(src_dir)
        self._build_dir = pathlib.Path(build_dir)

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return ["block_size"]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return []

    def build_bench(self, block_size: int, **kwargs) -> None:
        build_dir = self._build_dir
        self.platform.comm.makedirs(path=build_dir, exist_ok=True)
        self.platform.comm.shell(
            command="cmake ..",
            current_dir=build_dir,
            output_is_log=True,
        )
        self.platform.comm.shell(
            command=f"cmake  -D VERIFY=true -D WGROUP_SIZE={block_size} .",
            current_dir=f"{build_dir}",
            output_is_log=True,
        )
        self.platform.comm.shell(
            command=f"cmake --build . --config Release --target {self._cmake_target}{self._parallel_make_str()}",
            current_dir=f"{build_dir}",
            output_is_log=True,
        )

    def single_run(self, **kwargs) -> str:
        current_dir = pathlib.Path.joinpath(self._build_dir, "./src")
        environment = self._preload_env(**kwargs)
        metrics_list = self._constants.get("profiling_metrics")
        if len(metrics_list) > 0:
            metrics = ",".join(metrics_list)
            # temp..? warmup run
            run_command = [
                f"./{self._cmake_target}",
                "&>/dev/null",
                "&&",
                "ncu",
                "--metrics",
                metrics,
                f"./{self._cmake_target}",
            ]
        else:
            run_command = [
                f"./{self._cmake_target}",
                "&>/dev/null",
                "&&",
                f"./{self._cmake_target}",
            ]
        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )
        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=wrapped_run_command,
            wrapped_environment=wrapped_environment,
            current_dir=current_dir,
            environment=environment,
            print_output=True,
        )
        return output

    def ncu_to_ms(self, value, unit_str) -> str:
        conv = {"usecond": 1000, "msecond": 1}
        return str(float(value) / conv[unit_str])

    def parse_output_to_results(
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}
        ncu_metrics = self._constants.get("profiling_metrics")
        smi_metrics = self._constants.get("smi_metrics")
        metrics = ["duration:", "kernel_time:"]
        for m in metrics:
            i = command_output.index(m)
            line = command_output[i:].splitlines()[0]
            left, right = line.rsplit(":")
            result_dict[left.strip()] = right.strip()
        for m in ncu_metrics:
            i = command_output.index(m + ".avg")
            line = command_output[i:].splitlines()[0]
            left, _u, right = line.rsplit()  # metric, unit, value
            result_dict[left.split(".avg")[0].strip()] = self.ncu_to_ms(right.strip(), _u)

        # smi
        if len(smi_metrics) > 0:
            with open(pathlib.Path("./src", "smi.csv").resolve(), "r") as file:
                reader = csv.reader(file)
                data = []
                for row in reader:
                    data.append(list(map(lambda r: re.findall(r"\d+", r), row)))
                data_transp = list(zip(*data))
                for i, row in enumerate(data_transp):
                    # drop header row which is now first el
                    els = [int(el_lst[0]) for el_lst in row[1:]]
                    result_dict[smi_metrics[i]] = sum(els) / len(els)

        result_dict["benchname"] = "sycl"
        return result_dict
