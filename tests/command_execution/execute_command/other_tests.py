# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from __future__ import annotations  # Otherwise Queue comlains about typing

from multiprocessing import Queue
import shlex
import subprocess
import sys
from time import sleep
from typing import Any

from benchkit.shell.CommunicationLayer.hooks.hook import IOResultHook, MergeErrToOut, OutputHook
from tests.command_execution.execute_command.util import script_path_string

from benchkit.shell.ast_shell_out import execute_command
from benchkit.shell.commandAST import command as makecommand
from benchkit.shell.commandAST.nodes.variable_node import RuntimeVariable
from benchkit.shell.commandAST.visitor import (
    execute_on_remote,
    getString,
    inline,
    printAst,
    resolveAllVariablesWithDict,
)
from benchkit.shell.CommunicationLayer.hooks.basic_hooks import (
    logger_line_hook,
    std_out_result_void_err,
    void_hook,
)
from benchkit.shell.CommunicationLayer.IO_stream import PipeIOStream, ReadableIOStream, WritableIOStream
from benchkit.shell.shell import pipe_shell_out, shell_interactive, shell_out, split_on_pipe


def commandtests():

    commandres = makecommand.command("'ls -R'", ["arg0", "arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = makecommand.command("'ls -R '", ["arg0", "arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = makecommand.command("' ls -R'", ["arg0", "arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = makecommand.command("ls -R", ["arg0", "arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = makecommand.command("ls -R   ", ["arg0", "arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = makecommand.command("   ls -R", ["arg0", "arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = makecommand.command("ls     -R", ["arg0", "arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = makecommand.command("ls", ["arg0", "arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    print("-------------------------------------------")
    commandres = makecommand.command("ls     -R", [RuntimeVariable("QQ", [1, 2]), "arg1"])


"""
Tests for the file to show that the functions are working
"""


def localtests():
    amount_of_time_to_sleep = RuntimeVariable("amountOfTimeToSleep", [1, 2, 5, 40])
    main_command_ast = makecommand.command("sleep", [amount_of_time_to_sleep])
    full_command = makecommand.command("perf stat", [inline(main_command_ast), "-a"])
    remote_command = execute_on_remote(full_command, "user@host", port=57429)
    printAst(remote_command)

    resolved_command = resolveAllVariablesWithDict(
        remote_command,
        {
            "amountOfTimeToSleep": "40",
        },
    )

    string = getString(resolved_command)

    print(string)


def newtest():
    c = makecommand.command("ssh user@host -p 57429 -t 'perf stat sleep 1'")
    printAst(c)
    string = getString(c)
    print(string)


def runtest():
    t = shlex.split("perf stat 'sleep 10' -a")
    print(t)

    main_command_ast = makecommand.command("sleep", ["1"])
    full_command = makecommand.command("perf stat", [inline(main_command_ast)])
    remote_command = execute_on_remote(full_command, "user@host", port=57429)
    printAst(remote_command)
    string = getString(remote_command)
    print(string)
    local_proc_1 = subprocess.Popen(
        string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    outs, errs = local_proc_1.communicate()
    retcode = local_proc_1.poll()
    output = outs
    print(retcode)
    print(str(output.decode("utf-8")))


def shell_test():
    a = pipe_shell_out('ls | cat')
    print(a)
    a = pipe_shell_out([script_path_string("runForever"), '|', 'cat'])
    print(a)

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
