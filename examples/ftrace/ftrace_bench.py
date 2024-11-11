import pathlib
from typing import Iterable, List
from benchkit.adb import AndroidDebugBridge
from benchkit.commandwrappers import CommandWrapper
from benchkit.platforms.generic import Platform
from benchkit.sharedlibs import SharedLib
from benchkit.utils.ftrace import FTrace
from benchkit.benchmark import Benchmark, CommandAttachment, PostRunHook, PreRunHook
from benchkit.utils.types import PathType


BUILD_VARIABLES = []
RUN_VARIABLES = []
TILT_VARIABLES = []

class FTraceBenchmark(Benchmark):
    def __init__(
        self,
        bench_dir: PathType,
        mobile: bool = False,
        command_wrappers: Iterable[CommandWrapper] = [],
        command_attachments: Iterable[CommandAttachment] = [],
        shared_libs: Iterable[SharedLib] = [],
        pre_run_hooks: Iterable[PreRunHook] = [],
        post_run_hooks: Iterable[PostRunHook] = [],
        platform: Platform | None = None,
        adb: AndroidDebugBridge | None = None,
    ) -> None:
        super().__init__(
            command_wrappers=command_wrappers,
            command_attachments=command_attachments,
            shared_libs=shared_libs,
            pre_run_hooks=pre_run_hooks,
            post_run_hooks=post_run_hooks,
        )
        self.bench_dir = bench_dir
        self.mobile = mobile
        
        if platform is not None:
            self.platform = platform
        if adb is not None:
            self.adb = adb


    @property
    def bench_src_dir(self) -> pathlib.Path:
        return pathlib.Path(self.bench_dir)

    @staticmethod
    def get_build_var_names() -> List[str]:
        return BUILD_VARIABLES

    @staticmethod
    def get_run_var_names() -> List[str]:
        return RUN_VARIABLES

    @staticmethod
    def get_tilt_var_names() -> List[str]:
        return TILT_VARIABLES 
    
    

def main() -> None:
    path = "./tests/tmp/ftrace_dump"
    trace = FTrace(path)
    spans = trace.query_spans()
    counts =trace.query_counts()
    for span in spans:
        print(span)
    for count in counts:
        print(count)


if __name__ == "__main__":
    main()
