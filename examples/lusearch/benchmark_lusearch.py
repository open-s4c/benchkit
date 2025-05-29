import pathlib
from typing import Any, Dict, Iterable, List, Optional

from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.campaign import CampaignCartesianProduct, Constants
from benchkit.commandwrappers import CommandWrapper
from benchkit.platforms import get_current_platform
from benchkit.dependencies.packages import PackageDependency
from benchkit.platforms import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.types import CpuOrder, PathType

class LusearchBench(Benchmark):
    """Benchmark object for lusearch benchmark."""

    def __init__(
        self,
        src_dir: PathType,
        command_wrappers: Iterable[CommandWrapper] = (),
        command_attachments: Iterable[CommandAttachment] = (),
        shared_libs: Iterable[SharedLib] = (),
        pre_run_hooks: Iterable[PreRunHook] = (),
        post_run_hooks: Iterable[PostRunHook] = (),
        platform: Platform | None = None,
        # build_dir: PathType | None = None,
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

        # TODO: (Theo) Maybe make source dir root of benchmark
        bench_src_path = pathlib.Path(src_dir)
        if not self.platform.comm.isdir(bench_src_path) and self.platform.comm.isfile(
            bench_src_path / "/build.xml"
        ):
            raise ValueError(
                f"Invalid lusearch source path: {bench_src_path}\n"
                "src_dir argument can be defined manually."
            )
        self._bench_src_path = bench_src_path

        # if build_dir is None:
        #     self._build_dir = self._bench_src_path / f"build-{self.platform.hostname}"
        #     self._tmpdb_dir = "/tmp/benchkit_leveldb_db"
        # else:
        #     self._build_dir = self._bench_src_path / build_dir
        #     self._tmpdb_dir = self._build_dir / "tmp" / "benchkit_leveldb_db"

    @property
    def bench_src_path(self) -> pathlib.Path:
        return self._bench_src_path

    @staticmethod
    def get_build_var_names() -> List[str]:
        return []

    @staticmethod
    def get_run_var_names() -> List[str]:
        return [
            "bench_name",
            "size",
            "nb_threads",
        ]

    # @staticmethod
    # def get_tilt_var_names() -> List[str]:
    #     return []

    @staticmethod
    def _parse_results(
        output: str,
        nb_threads: int,
    ) -> Dict[str, str]:
        duration = ""
        for line in output.split('\n'):
            if line.startswith("===== DaCapo processed"):
                splits = line.split(' ')
                duration = splits[6]
                print("line:", splits)
        # benchstats = output.split("benchstats:")[-1].strip()
        # values = benchstats.split(";")

        # if len(values) != nb_threads + 2:
        #     raise ValueError(f"Incoherent output from lusearch, please check output:\n {output}")

        # names = ["duration", "global_count"] + [f"thread_{k}" for k in range(nb_threads)]
        # result_dict = dict(zip(names, values))

        # computed_duration = float(result_dict.get("duration")) / nb_threads
        # result_dict["duration"] = str(computed_duration)

        return {
                "duration" : duration
                }

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("build-essential"),
            PackageDependency("cmake"),
        ]

    # def build_tilt(self, **kwargs) -> None:
    #     self.tilt.build_single_lock(**kwargs)

    def prebuild_bench(self, **_kwargs) -> None:
        # build_dir = self._build_dir
        # self.platform.comm.makedirs(path=build_dir, exist_ok=True)

        # must_debug = self.must_debug()
        # cmake_build_type = "Debug" if must_debug else "Release"

        # self.platform.comm.shell(
        #     command=f"cmake -DCMAKE_BUILD_TYPE={cmake_build_type} {self._bench_src_path}",
        #     current_dir=build_dir,
        #     output_is_log=True,
        # )
        if False:
            self.platform.comm.shell(
                command=f"ant lusearch",
                current_dir=self._bench_src_path,
                output_is_log=True,
            )
        # if not self.platform.comm.isdir(self._tmpdb_dir):
        #     self.platform.comm.makedirs(path=self._tmpdb_dir, exist_ok=True)
        #     db_init_command = [
        #         "./db_bench",
        #         "--threads=1",
        #         "--benchmarks=fillseq",
        #         f"--db={self._tmpdb_dir}",
        #     ]
        #     self.platform.comm.shell(command=db_init_command, current_dir=build_dir)

    def build_bench(
        self,
        **kwargs,
    ) -> None:
        pass

    def clean_bench(self) -> None:
        pass

    def single_run(  # pylint: disable=arguments-differ
        self,
        benchmark_duration_seconds: int,
        size: str = "",
        nb_threads: int = 2,
        bench_name: str = "readrandom",
        **kwargs,
    ) -> str:
        # if freshdb_foreach_run:
        #     db_init_command = [
        #         "./db_bench",
        #         "--threads=1",
        #         "--benchmarks=fillseq",
        #         f"--db={self._tmpdb_dir}",
        #     ]
        #     self.platform.comm.shell(
        #         command=db_init_command,
        #         current_dir=self._build_dir,
        #         print_output=False,
        #     )

        environment = self._preload_env(
            size=size,
            **kwargs,
        )

        """
        Notice that, distinct from other LevelDb benchmarks using the `num` parameter,
        `readreverse` and `readsequential` benchmarks have a very short duration.
        As such, consider increasing the size of `num` for those.
        """
        # if bench_name in ["readrandom", "readmissing", "readhot", "seekrandom"]:
        #     duration_num = f"--duration={benchmark_duration_seconds}"
        # else:
        #     duration_num = f"--num={num // nb_threads}"

        # if bench_name in [
        #     "fillseq",
        #     "fillrandom",
        #     "fillsync",
        #     "fill100K",
        # ]:
        #     use_existing_db = False
        # else:
        #     use_existing_db = True

        run_command = [
            "java",
            "-jar",
            "dacapo-evaluation-git-4e3de06d.jar",
            "lusearch",
            f"--thread-count={nb_threads}",
            f"--size={size}",
            f"--iterations=1",
        ]

        wrapped_run_command, wrapped_environment = self._wrap_command(
            run_command=run_command,
            environment=environment,
            size=size,
            nb_threads=nb_threads,
            **kwargs,
        )

        output = self.run_bench_command(
            run_command=run_command,
            wrapped_run_command=run_command,
            current_dir=self._bench_src_path,
            environment=environment,
            wrapped_environment=environment,
            print_output=False,
        )
        return output

    def parse_output_to_results(  # pylint: disable=arguments-differ
        self,
        command_output: str,
        run_variables: Dict[str, Any],
        **_kwargs,
    ) -> Dict[str, Any]:
        nb_threads = int(run_variables["nb_threads"])
        result_dict = self._parse_results(output=command_output, nb_threads=nb_threads)
        return result_dict


def lusearch_campaign(
    name: str = "lusearch_campaign",
    benchmark: Optional[LusearchBench] = None,
    bench_name: Iterable[str] = ("lusearch",),
    src_dir: Optional[PathType] = None,
    # build_dir: Optional[str] = None,
    results_dir: Optional[PathType] = None,
    command_wrappers: Iterable[CommandWrapper] = (),
    command_attachments: Iterable[CommandAttachment] = (),
    shared_libs: Iterable[SharedLib] = (),
    pre_run_hooks: Iterable[PreRunHook] = (),
    post_run_hooks: Iterable[PostRunHook] = (),
    platform: Platform | None = None,
    nb_runs: int = 1,
    benchmark_duration_seconds: int = 5,
    size: Iterable[str] = ("default",),
    nb_threads: Iterable[int] = (1,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Constants = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    """Return a cartesian product campaign configured for the lusearch benchmark."""
    variables = {
        "size": size,
        "nb_threads": nb_threads,
        "bench_name": bench_name,
    }
    if pretty is not None:
        pretty = {"size": pretty}

    if src_dir is None:
        pass  # TODO try some search heuristics

    if benchmark is None:
        benchmark = LusearchBench(
            src_dir=src_dir,
            command_wrappers=command_wrappers,
            # command_attachments=command_attachments,
            command_attachments=[
                lambda process, record_data_dir: command_wrappers[0].attach_every_thread(
                    platform=get_current_platform(),
                    process=process,
                    record_data_dir=record_data_dir,
                    poll_ms=100,
                    use_jvm=True,
                    ),
                ],
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
            platform=platform,
            # build_dir=build_dir,
        )

    return CampaignCartesianProduct(
        name=name,
        benchmark=benchmark,
        nb_runs=nb_runs,
        variables=variables,
        constants=constants,
        debug=debug,
        gdb=gdb,
        enable_data_dir=enable_data_dir,
        continuing=continuing,
        benchmark_duration_seconds=benchmark_duration_seconds,
        results_dir=results_dir,
        pretty=pretty,
    )
