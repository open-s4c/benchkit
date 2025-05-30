from benchkit.commandwrappers.jvmxlog import JVMXlogWrap
from benchkit.commandwrappers.perf import PerfReportWrap, PerfStatWrap


class SpeedupStackWrapper():
    def __init__(self) -> None:
        self.perfstatwrap = PerfStatWrap(
                perf_path=None,
                events=[
                    # "cache-misses",
                    "context-switches"
                    # "sched:sched_switch"
                    ],
                use_json = False,
                wrap_command = False,
                separator=";",
                quiet=False,
                remove_absent_event=False,
                )

        self.jvmxlogwrap = JVMXlogWrap()

        self.perfreportwrap = PerfReportWrap(
                wrap_command = False,
                perf_record_options = ["-e", "syscalls:sys_enter_futex,syscalls:sys_exit_futex"],
                perf_report_options = [],
                report_file = True,
                report_interactive = False,
                script = True,
                use_jvm = True,
                )

    def command_wrappers(self):
        return [self.perfstatwrap, self.jvmxlogwrap, self.perfreportwrap]

    def post_run_hooks(self):
        return [self.perfstatwrap.post_run_hook_update_results,
                self.jvmxlogwrap.post_run_hook_update_results,
                self.perfreportwrap.post_run_hook_report]
