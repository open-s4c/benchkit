import pathlib
from typing import Any, Dict, Iterable, List

from benchkit.benchmark import (
    Benchmark,
    CommandAttachment,
    CommandWrapper,
    PostRunHook,
    PreRunHook,
    SharedLib,
)
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform, get_current_platform
from benchkit.utils.misc import TimeMeasure
from benchkit.utils.types import PathType


class SequentialDPLL(Benchmark):

    def __init__(
        self,
        src_dir: PathType,
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
        self._tmp_results = {}
        if platform is not None:
            self.platform = platform  # TODO Warning! overriding upper class platform
        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path):
            raise ValueError(
                f"Invalid source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self.platform = get_current_platform()
        self._bench_src_path = bench_src_path
        self._build_dir = bench_src_path

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return ["implementation"]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return ["instance", "implementation"]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + []

    def build_tilt(self, **kwargs) -> None:
        pass

    def prebuild_bench(
        self,
        **_kwargs,
    ) -> None:
        pass

    def build_bench(
        self,
        implementation: str,
        **kwargs,
    ) -> None:
        self.platform.comm.shell(
            command="make",
            current_dir=implementation,
            output_is_log=True,
        )

    def clean_bench(self) -> None:
        pass

    def single_run(
        self,
        benchmark_duration_seconds: int,
        instance: str,
        implementation: str,
        **kwargs,
    ) -> str:
        environment = {}
        print(benchmark_duration_seconds)
        run_command = [implementation + "/Main", instance]
        wrap_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        with TimeMeasure() as time_measure:
            output = self.run_bench_command(
                run_command=run_command,
                wrapped_run_command=wrap_run_command,
                current_dir=self._build_dir,
                environment=environment,
                wrapped_environment=wrapped_environment,
                print_output=False,
            )
        self._tmp_results["runtime_s"] = time_measure.duration_seconds
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        result_dict = {}
        result_dict["instance"] = pathlib.Path(run_variables["instance"]).stem
        result_dict["implementation"] = pathlib.Path(run_variables["implementation"]).stem
        # Parsing summary
        return result_dict | self._tmp_results


class ParallelDPLL(Benchmark):

    def __init__(
        self,
        src_dir: PathType,
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
            self.platform = platform  # TODO Warning! overriding upper class platform
        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path):
            raise ValueError(
                f"Invalid source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._tmp_results = {}
        self.platform = get_current_platform()
        self._bench_src_path = bench_src_path
        self._build_dir = bench_src_path

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return ["implementation"]

    @staticmethod
    def get_run_var_names() -> List[str]:
        return ["instance", "implementation", "num_threads"]

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return []

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + []

    def build_tilt(self, **kwargs) -> None:
        pass

    def prebuild_bench(
        self,
        **_kwargs,
    ) -> None:
        pass

    def build_bench(
        self,
        implementation: str,
        **kwargs,
    ) -> None:
        self.platform.comm.shell(
            command="make",
            current_dir=implementation,
            output_is_log=True,
        )

    def clean_bench(self) -> None:
        pass

    def single_run(
        self,
        benchmark_duration_seconds: int,
        instance: str,
        implementation: str,
        num_threads: int,
        **kwargs,
    ) -> str:
        environment = {}
        run_command = [implementation + "/Main", instance, "-t", str(num_threads)]
        wrap_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            **kwargs,
        )

        with TimeMeasure() as time_measure:
            output = self.run_bench_command(
                run_command=run_command,
                wrapped_run_command=wrap_run_command,
                current_dir=self._build_dir,
                environment=environment,
                wrapped_environment=wrapped_environment,
                print_output=False,
            )
        self._tmp_results["runtime_s"] = time_measure.duration_seconds
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:

        result_dict = {}
        result_dict["instance"] = pathlib.Path(run_variables["instance"]).stem
        result_dict["implementation"] = pathlib.Path(run_variables["implementation"]).stem
        # Parsing summary
        return result_dict | self._tmp_results
