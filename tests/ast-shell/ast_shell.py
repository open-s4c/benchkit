# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import shlex
import subprocess

from benchkit.shell.ast_shell_out import shell_out_new
from benchkit.shell.commandAST import command as makecommand
from benchkit.shell.commandAST.nodes.variable_node import RuntimeVariable
from benchkit.shell.commandAST.visitor import (
    execute_on_remote,
    getString,
    inline,
    printAst,
    resolveAllVariablesWithDict,
)


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


def test():

    # THE TWO EXAMPLES BELOW DONT HALT
    # They exist to show that functions work in an intuative manner.

    a = shell_out_new(
        "ls", print_output=True, output_is_log=True, redirect_stderr_to_stdout=False
    )
    print("--------------------")
    print(a)

    # To show that output is log works
    # a = shell_out_new(
    #     "cat /dev/random", print_output=True, output_is_log=True
    # )
    # print("--------------------")
    # print(a)
    # To show that input works
    # shell_out_new(
    #     "ssh user@host -p 22 'cat'", output_is_log=True, std_input="wafel\n" \
    #     "aeu aeu\n"
    # )


    # a = shell_out_new(
    #     "ssh user@host -p 22 'perf stat sleep 1'", print_output=True, output_is_log=True,redirect_stderr_to_stdout=False
    # )
    # print("--------------------")
    # print(a)
    # shell_out_new(["ssh", "user@host", "-p", "57429", "-t", "perf stat sleep 1"])
    # main_command_ast = makecommand.command("sleep", ["1"])
    # full_command = makecommand.command("perf stat", [inline(main_command_ast)])
    # remote_command = execute_on_remote(full_command, "user@host", port=57429)
    # shell_out_new(remote_command)


if __name__ == "__main__":
    # commandtests()
    # localtests()
    # newtest()
    # runtest()
    test()
