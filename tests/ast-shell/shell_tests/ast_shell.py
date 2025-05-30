# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import itertools
import pathlib
import re
import subprocess
import unittest
from typing import Any

from shell_scripts import TestTimeout, script_path_string, timeout

from benchkit.shell.ast_shell_out import (
    convert_command_to_ast,
    shell_out_new,
    try_converting_bystring_to_readable_characters,
)

# Due to print statements being inside of threads unittest does
# not allow us to check the output of stdout.
# We will have to write tests in a different way to check what the user sees.
# To this end these tests only test functionality


def get_arguments_dict_list(
    overwrite_arguments_dict: dict[str, Any] | None = None, include_cosmetic: bool = True
):
    if overwrite_arguments_dict is None:
        overwrite_arguments_dict = {}

    arguments_dict = {}
    if include_cosmetic:
        arguments_dict = {
            "print_output": [True, False],
            "output_is_log": [True, False],
        }

    for argument_key in overwrite_arguments_dict:
        arguments_dict[argument_key] = overwrite_arguments_dict[argument_key]

    keys = []
    arguments = []

    for key, arugments in arguments_dict.items():
        keys.append(key)
        arguments += [arugments]
    argument_permutations = itertools.product(*arguments)
    result_list = []
    for argument_permutation in list(argument_permutations):
        result_list.append(dict(zip(keys, argument_permutation)))
    return result_list


class BasicShellTests(unittest.TestCase):

    # @unittest.skip("disabled for debugging")
    def test_echo(self):
        """Basic tests to see if the command-line can execute a given command
        and return the correct output given a range of arguments"""
        argument_list = get_arguments_dict_list(
            {
                "redirect_stderr_to_stdout": [True, False],
                "current_dir": [None, pathlib.Path(__file__).parent.resolve()],
                "environment": [None, {"test": "test"}],
                "timeout": [None, 20],
                "ignore_ret_codes": [(), (1,)],
            }
        )
        for args in argument_list:
            with timeout(1):
                # test echo with multiple parameters to make sure none mess up the result
                a = shell_out_new(
                    convert_command_to_ast(f"echo benchkit_echo_test {str(args)}"),
                    print_command=True,
                    **args,
                )
                print(a)
                expeced_result = re.sub(r"\'", "", f"benchkit_echo_test {str(args)}")
                print(expeced_result)
                self.assertEqual(
                    try_converting_bystring_to_readable_characters(a),
                    f"{expeced_result}\n",
                    "shell does not provide the right output in the result",
                )

    # @unittest.skip("disabled for debugging")
    def test_run_forever(self):
        """Test to make sure that commands do not exit prematurely"""
        argument_list = get_arguments_dict_list(
            {
                "redirect_stderr_to_stdout": [True, False],
                "current_dir": [None, pathlib.Path(__file__).parent.resolve()],
                "environment": [None, {"test": "test"}],
                "timeout": [None, 20],
                "ignore_ret_codes": [(), (1,)],
            }
        )
        for args in argument_list:
            with self.assertRaises(TestTimeout):
                with timeout(5):
                    shell_out_new(convert_command_to_ast(script_path_string("runForever")), **args)

    # @unittest.skip("disabled for debugging")
    def test_timeout(self):
        """testing the timeout argument"""
        argument_list = get_arguments_dict_list(
            {
                "redirect_stderr_to_stdout": [True, False],
                "current_dir": [None, pathlib.Path(__file__).parent.resolve()],
                "environment": [None, {"test": "test"}],
                "ignore_ret_codes": [(), (1,)],
                "timeout": [1, 2],  # tested argument
            }
        )
        # making sure that a program times out due to the argument
        for args in argument_list:
            with timeout(5):
                with self.assertRaises(subprocess.TimeoutExpired):
                    shell_out_new(convert_command_to_ast(script_path_string("runForever")), **args)

        argument_list = get_arguments_dict_list(
            {
                "redirect_stderr_to_stdout": [True, False],
                "current_dir": [None, pathlib.Path(__file__).parent.resolve()],
                "environment": [None, {"test": "test"}],
                "ignore_ret_codes": [(), (1,)],
                "timeout": [6],  # tested argument
            }
        )

        # making sure that it does not time out before the given timeout
        for args in argument_list:
            with self.assertRaises(TestTimeout):
                with timeout(5):
                    shell_out_new(convert_command_to_ast(script_path_string("runForever")), **args)

    # @unittest.skip("disabled for debugging")
    def test_input(self):
        """testing the use of the std_input parameter"""
        argument_list = get_arguments_dict_list(
            {
                "redirect_stderr_to_stdout": [True, False],
                "current_dir": [None, pathlib.Path(__file__).parent.resolve()],
                "environment": [None, {"test": "test"}],
                "ignore_ret_codes": [(), (1,)],
            }
        )

        for args in argument_list:
            with timeout(10):
                out = shell_out_new(
                    convert_command_to_ast(script_path_string("writeBack")),
                    std_input=f"benchkit input test {str(args)}\n",
                    **args,
                )
                self.assertEqual(
                    try_converting_bystring_to_readable_characters(out),
                    f"benchkit input test {str(args)}\n",
                    f"recieved{out}",
                )

    # @unittest.skip("disabled for debugging")
    def test_command_blocks_io_overfull(self):
        """Overfull internal IO buffers would halt the execution of the command
        Here we test whether or not this happens in our implementation
        """
        argument_list = get_arguments_dict_list(
            {
                "redirect_stderr_to_stdout": [True, False],
                "current_dir": [None, pathlib.Path(__file__).parent.resolve()],
                "environment": [None, {"test": "test"}],
                "timeout": [None, 20],
                "ignore_ret_codes": [(), (1,)],
            }
        )

        for args in argument_list:
            try:
                with timeout(20):
                    # tests for filling the std_err
                    shell_out_new(
                        convert_command_to_ast(script_path_string("fillErrThenOut")), **args
                    )
            except TestTimeout:
                self.fail(
                    f"the command got halted during excecution for \
                        {script_path_string('fillErrThenOut')} with args: {args}"
                )
                raise TestTimeout

            try:
                with timeout(20):
                    # tests for filling the std_io
                    shell_out_new(
                        convert_command_to_ast(script_path_string("fillOutThenErr")), **args
                    )
            except TestTimeout:
                self.fail("the command got halted during excecution")
                raise TestTimeout

    # @unittest.skip("disabled for debugging")
    def test_ignore_return_codes(self):
        """Overfull internal IO buffers would halt the execution of the command
        Here we test whether or not this happens in our implementation
        """

        # test that success value does not throw an error regardles of ignore ret_codes
        argument_list = get_arguments_dict_list(
            {
                "redirect_stderr_to_stdout": [True, False],
                "current_dir": [None, pathlib.Path(__file__).parent.resolve()],
                "environment": [None, {"test": "test"}],
                "timeout": [None, 20],
                "ignore_ret_codes": [
                    (),
                    (
                        1,
                        4,
                    ),
                    (
                        2,
                        7,
                    ),
                    (
                        4,
                        5,
                    ),
                    (63,),
                    (0,),
                ],
                "success_value": [1, 6, 53, 19],
            }
        )

        for args in argument_list:
            try:
                with timeout(20):
                    # tests for filling the std_err
                    retcode_to_output = args["success_value"]
                    shell_out_new(
                        convert_command_to_ast(script_path_string("returnExitCode")),
                        **args,
                        std_input=f"{retcode_to_output}\n",
                    )
            except TestTimeout:
                self.fail(
                    f"the command got halted during excecution for \
                        {script_path_string('fillErrThenOut')} with args: {args}"
                )
                raise TestTimeout

        # test that error codes in ignore list do not throw error
        argument_list = get_arguments_dict_list(
            {
                "redirect_stderr_to_stdout": [True, False],
                "current_dir": [None, pathlib.Path(__file__).parent.resolve()],
                "environment": [None, {"test": "test"}],
                "timeout": [None, 20],
                "ignore_ret_codes": [
                    (),
                    (
                        1,
                        4,
                    ),
                    (
                        2,
                        7,
                    ),
                    (
                        4,
                        5,
                    ),
                    (63,),
                    (0,),
                ],
                "output_is_log": [True],
            }
        )

        for args in argument_list:
            try:
                with timeout(20):
                    retcode_to_output = (
                        args["ignore_ret_codes"][len(args["ignore_ret_codes"]) - 1 % 3]
                        if len(args["ignore_ret_codes"]) > 0
                        else 0
                    )
                    shell_out_new(
                        convert_command_to_ast(script_path_string("returnExitCode")),
                        **args,
                        std_input=f"{retcode_to_output}\n",
                    )
            except TestTimeout:
                self.fail(
                    f"the command got halted during excecution for \
                        {script_path_string('fillErrThenOut')} with args: {args}"
                )
                raise TestTimeout

        # test that error code still throws an error
        argument_list = get_arguments_dict_list(
            {
                "redirect_stderr_to_stdout": [True, False],
                "current_dir": [None, pathlib.Path(__file__).parent.resolve()],
                "environment": [None, {"test": "test"}],
                "timeout": [None, 20],
                "ignore_ret_codes": [
                    (),
                    (
                        1,
                        4,
                    ),
                    (
                        2,
                        7,
                    ),
                    (
                        4,
                        5,
                    ),
                    (63,),
                    (0,),
                ],
                "success_value": [0, 1, 6, 53, 19],
            }
        )

        for args in argument_list:
            try:
                with self.assertRaises(subprocess.CalledProcessError):
                    with timeout(20):
                        # tests for filling the std_err
                        retcode_to_output = (
                            3
                            + args["success_value"]
                            + (
                                args["ignore_ret_codes"][len(args["ignore_ret_codes"]) - 1 % 3]
                                if len(args["ignore_ret_codes"]) > 0
                                else args["success_value"]
                            )
                        )
                        print("----------------------")
                        print(retcode_to_output)
                        shell_out_new(
                            convert_command_to_ast(script_path_string("returnExitCode")),
                            **args,
                            std_input=f"{retcode_to_output}\n",
                        )
            except TestTimeout:
                self.fail(
                    f"the command got halted during excecution for \
                        {script_path_string('fillErrThenOut')} with args: {args}"
                )
                raise TestTimeout


if __name__ == "__main__":
    unittest.main()
