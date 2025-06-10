# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import shlex
import subprocess
import sys

from shell_scripts import script_path_string

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
    logger_hook,
    std_out_result_void_err,
)
from benchkit.shell.CommunicationLayer.IO_stream import PipeIOStream, ReadableIOStream
from benchkit.shell.shell import pipe_shell_out, shell_interactive, shell_out


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
    # args = {
    #     "print_output": True,
    #     "output_is_log": True,
    #     "redirect_stderr_to_stdout": False,
    #     "current_dir": None,
    #     "environment": None,
    #     "timeout": None,
    #     "ignore_ret_codes": (),
    # }
    # shell_out_new(convert_command_to_ast(script_path_string("fillOutThenErr")), **args)
    # print("yeet")

    # test for the newlines
    # raw_output = shell_out(
    #     command="cat",
    #     std_input="a \n\n b \n c\n",
    #     print_input=False,
    #     print_output=False,
    # )

    # test for command that does not fully output in deafault terminal

    # def pasalong(input_stream:ReadableIOStream,_) -> None:
    #     outline = input_stream.read(10)
    #     print(f'outline{outline!r}')
    #     while outline:
    #         print(f'outline{outline}')
    #         outline = input_stream.read(10)

    # a = StdinIOStream(sys.stdin)

    # pasalong(a,2)
    # ssh aaronb@soft24.vub.ac.be sleep 10
    # shell_interactive(
    #     # command=['ssh', 'aaronb@soft24.vub.ac.be', 'ls -A -w 1'],
    #     # command=['ssh', 'aaronb@soft24.vub.ac.be', 'sleep 10'],
    #     command=['sh'],
    #     # output_is_log=True
    # )
    shell_out(
        # command=['/home/aaronb/Documents/benchFork/benchkit/tests/ast-shell/shell_tests/shell_scripts/runForever.sh'],
        # command=['ssh', 'aaronb@soft24.vub.ac.be', 'sleep 10'],
        # command=['ls'],
        command="/home/aaron/benchkitFork/benchkit/tests/ast-shell/shell_tests/shell_scripts/runForever.sh",
        output_is_log=True,
        timeout=5,
    )

    # pipe_shell_out(
    #     [
    #         "/home/aaron/benchkitFork/benchkit/tests/ast-shell/shell_tests/shell_scripts/runForever.sh","cat"
    #     ]
    # )
    print("a")
    # print(a)
    # raw_output = shell_out(
    #     command="/usr/bin/perf list --no-desc",
    #     output_is_log=True,
    # )
    # return raw_output


if __name__ == "__main__":
    testhalt()
