# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.commandwrappers.javaperf import JavaPerfReportWrap, JavaPerfStatWrap
from benchkit.commandwrappers.jvmxlog import JVMXlogWrap
from benchkit.platforms import get_current_platform


class SpeedupStackWrapper:
    def __init__(self) -> None:
        self.javaperfstatwrap = JavaPerfStatWrap(
            perf_path=None,
            events=[
                # "cache-misses",
                "context-switches"
                # "sched:sched_switch"
            ],
            use_json=False,
            separator=";",
            quiet=False,
            remove_absent_event=False,
        )

        self.jvmxlogwrap = JVMXlogWrap()

        self.javaperfreportwrap = JavaPerfReportWrap(
            perf_record_options=["-e", "syscalls:sys_enter_futex,syscalls:sys_exit_futex"],
            perf_report_options=[],
            report_file=True,
            report_interactive=False,
        )

    def command_wrappers(self):
        return [self.jvmxlogwrap]

    def command_attachments(self):
        return [
                    lambda process, record_data_dir: self.javaperfstatwrap.attach_every_thread(
                        platform=get_current_platform(),
                        process=process,
                        record_data_dir=record_data_dir,
                        poll_ms=100,
                    ),
                    lambda process, record_data_dir: self.javaperfreportwrap.attach_every_thread(
                        platform=get_current_platform(),
                        process=process,
                        record_data_dir=record_data_dir,
                    ),
                ]

    def post_run_hooks(self):
        return [
            self.javaperfstatwrap.post_run_hook_update_results,
            self.jvmxlogwrap.post_run_hook_update_results,
            self.javaperfreportwrap.post_run_hook_report,
        ]
