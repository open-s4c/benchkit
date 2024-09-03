import csv
import pathlib
import re
from typing import Any, Dict, List

from benchkit.benchmark import Benchmark
from benchkit.platforms import Platform
from benchkit.utils.types import PathType


class OpclBench(Benchmark):
    def __init__(
        self,
        platform: Platform,
        src_dir: PathType,
        file_name: str,
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
        self.file_name = file_name
        self._bench_src_path = pathlib.Path(src_dir)

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return ["block_size"]

    def build_bench(self, **kwargs) -> None:
        return

    def single_run(self, block_size: int, **kwargs) -> str:
        current_dir = self._bench_src_path
        environment = self._preload_env(**kwargs)
        run_command = ["python3", f"{self.file_name}.py", f"{block_size}"]

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

    def parse_output_to_results(
        self,
        command_output: str,
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}
        smi_metrics = self._constants.get("smi_metrics")
        metrics = ["duration:", "kernel_time:"]
        for m in metrics:
            i = command_output.index(m)
            line = command_output[i:].splitlines()[0]
            left, right = line.rsplit(":")
            result_dict[left.strip()] = right.strip()

        # smi.. output not in command_output
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

        result_dict["benchname"] = "opencl"
        return result_dict
