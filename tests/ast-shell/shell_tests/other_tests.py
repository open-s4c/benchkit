# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import shlex
import subprocess
import sys

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

from shell_scripts import TestTimeout, script_path_string, timeout
from benchkit.shell.ast_shell_out import shell_out_new


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

def testhalt():
    # shell_process = subprocess.Popen(
    #     # why exec:
    #     # we want to be able to use shell=True
    #     # however this would make the shell the pid of the subprocess
    #     # by using exec we can get make the command take over the pid of the shell
    #     # this only works for POSIX
    #     f"./shell_scripts/fillErrThenPrint.sh",
    #     # shell=True,
    #     stdout=sys.stdout,
    #     stderr=sys.stderr,
    #     stdin=subprocess.PIPE,
    # )
    # shell_process.wait()
    out = shell_out_new(script_path_string('fillErrThenOut'),redirect_stderr_to_stdout=True,output_is_log=True)
    print("yeet")

if __name__ == "__main__":
    testhalt()