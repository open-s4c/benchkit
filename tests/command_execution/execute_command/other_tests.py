# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from __future__ import annotations  # Otherwise Queue comlains about typing

from multiprocessing import Queue
from pathlib import Path
import shlex
import subprocess
from time import sleep
from typing import Any

from benchkit.shell.command_execution.io.hooks.basic_hooks import logger_line_hook, std_out_result_void_err, void_hook
from benchkit.shell.command_execution.io.hooks.hook import MergeErrToOut
from tests.command_execution.execute_command.util import script_path_string

from benchkit.shell.command_execution.execute import execute_command

from benchkit.shell.command_execution.io.stream import PipeIOStream, ReadableIOStream, StringIOStream, WritableIOStream
from benchkit.shell.shell import pipe_shell_out, shell_interactive, shell_out, split_on_pipe


def shell_test():
    command = [script_path_string("runForever")]

    log_ls = logger_line_hook(
                f"\033[34m[OUT | ls]\033[0m" + " {}",
                f"\033[91m[ERR | ls]\033[0m" + " {}",
            )

    outobj, outhook = std_out_result_void_err()

    merge = MergeErrToOut()

    ls_command = execute_command(command,
                                timeout=2,
                                ordered_output_hooks=[
                                    merge,
                                    log_ls,
                                    # outhook,
                                    void_hook(),
                                    ]
                                )
    try:
        ls_command.get_return_code()
    except:
        sleep(5)


    # log_ls = logger_line_hook(
    #         f"\033[34m[OUT | sudo]\033[0m" + " {}",
    #         f"\033[91m[ERR | sudo]\033[0m" + " {}",
    #     )
    # filewriterIO = write_to_file_hook(Path("/tmp/testfile.txt"))
    # filewriter = OutputHook(filewriterIO,None)

    # a = execute_command(
    #     shlex.split("ssh aaronb@soft67.vub.ac.be 'sudo -S -k ls'"),
    #     ordered_input_hooks=[stream_prepend_hook(StringIOStream("123456789"))],
    #     ordered_output_hooks=[log_ls,MergeErrToOut(),filewriter,void_hook()]
    # )

    # a.get_return_code()

    # sleep(1)


    # a = pipe_shell_out('sudo perf stat ls')
    # print(a)
    # a = pipe_shell_out([script_path_string("runForever"), '|', 'cat'])
    # print(a)

    # shell_interactive("ssh aaronb@soft24.vub.ac.be 'sh'")


def testhalt():

    # -------------------------------------------------------
    # pid hook example
    # for end
    # -------------------------------------------------------

    def stdout_pid_result_filter(inputStream:ReadableIOStream,OutputStream:WritableIOStream,queue:Queue[Any]):
        first_line = inputStream.read_line()
        queue.put(first_line)
        outline = inputStream.read(10)
        while outline:
            OutputStream.write(outline)
            outline = inputStream.read(10)

    pid_stream_hook = IOResultHook(stdout_pid_result_filter)


    pid_output_hook = OutputHook(pid_stream_hook,None)

    # -------------------------------------------------------
    # commands work
    # first step
    # get return codes/errors
    # -------------------------------------------------------

    # process_dir = execute_command(["mkdir", "test"],ordered_output_hooks=[void_hook()])
    # print(process_dir.get_return_code())

    # execute_command(["command that does not exist"])

    # wrong_retcode = execute_command(["cat", "wafel"],
    #                                 # success_value=1,
    #                                 # ignore_ret_codes=(1,),
    #                                 ordered_output_hooks=[void_hook()])
    # print(wrong_retcode.get_return_code())

    # -------------------------------------------------------
    # ls
    # -> does not work
    #   -> voidhook
    #     -> drawio
    # -> would be nice to see what it is doing
    #   -> log_ls
    #     -> show
    #       -> drawio
    # -> would be nice to get output
    #   -> output
    #     -> drawio
    # -> move over to pipe cat
    # -------------------------------------------------------

    # command = ["ls"]
    command = [script_path_string("runForever")]

    log_ls = logger_line_hook(
                f"\033[34m[OUT | ls]\033[0m" + " {}",
                f"\033[91m[ERR | ls]\033[0m" + " {}",
            )

    outobj, outhook = std_out_result_void_err()

    merge = MergeErrToOut()

    ls_command = execute_command(command,
                        ordered_output_hooks=[
                            merge,
                            log_ls,
                            # outhook,
                            # void_hook(),
                            ]
                        )

    # print(outobj.get_result())
    # print(ls_command.get_return_code())

    ls_out_stream = ls_command.get_output().std_out

    log_cat = logger_line_hook(
                f"\033[34m[OUT | cat]\033[0m" + " {}",
                f"\033[91m[ERR | cat]\033[0m" + " {}",
            )

    # cat_command_string = ["cat"]
    # cat_command_string = shlex.split("ssh aaronb@soft24.vub.ac.be 'cat'")
    cat_command_string = shlex.split("ssh aaronb@soft24.vub.ac.be 'echo $$; cat'")

    cat_command = execute_command(cat_command_string,
                        std_input=ls_out_stream,
                        ordered_output_hooks=[
                            pid_output_hook,
                            log_cat,
                            # outhook,
                            void_hook(),
                            ]
                        )

    print(f'-------\n{pid_stream_hook.get_result()}\n----------')

    ls_command.get_return_code()
    cat_command.get_return_code()




    # these can not be reused
    # log = logger_line_hook(
    #             f"\033[34m[OUT | ]\033[0m" + " {}",
    #             f"\033[91m[ERR | ]\033[0m" + " {}",
    #         )

    # a = execute_command(
    #     shlex.split("ssh aaronb@soft24.vub.ac.be 'cd test; echo $$; exec sudo -S env varname=varvalue printenv varname'"),
    #     ordered_output_hooks=[log]
    # )



    # r = a.get_return_code()
    # print(r)


if __name__ == "__main__":
    # testhalt()
    shell_test()
