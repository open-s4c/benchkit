# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Unit tests of shell module.

TODO move into tests dir.
"""

import os
import os.path
import shutil
import subprocess
import tempfile
import time
import unittest
from io import StringIO
from unittest.mock import patch

from benchkit.communication import LocalCommLayer
from benchkit.shell.shell import shell_out
from benchkit.shell.utils import (
    _print_cd,
    _print_env,
    _print_file_shell_cmd,
    _print_run,
    _print_shell_cmd,
    _shell_cmd,
    get_args,
)


class TestShell(unittest.TestCase):
    """Unit tests for shell utils."""

    def test_get_args(self):
        """test get_args"""
        args = ["arg1", "arg2a arb2b", "arg3"]
        self.assertEqual(get_args(args), args)

        # TODO: the following does not work if there are arguments with spaces:
        arg_str = 'arg1 "arg2a arg2b" arg3'
        self.assertNotEqual(get_args(arg_str), args)  # TODO switch with assertEqual once it works

        arg_str = "arg1 arg2 arg3"
        self.assertEqual(get_args(arg_str), ["arg1", "arg2", "arg3"])

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_cd(self, mock_stdout):
        """test print_cd"""
        _print_cd("directory")
        self.assertEqual(mock_stdout.getvalue(), "[CD] directory\n")

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_env(self, mock_stdout):
        """test print_env"""
        env = {"key1": "value1", "key2": "value2"}
        _print_env(env)
        _print_env(None)
        self.assertEqual(
            mock_stdout.getvalue(),
            "[ENV:key1] value1\n[ENV:key2] value2\n",
        )

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_run(self, mock_stdout):
        """test print_run"""
        args = ["arg1", "arg2a arg2b", "arg3"]
        _print_run(args)
        _print_run(arguments=args, asynced=True)
        self.assertEqual(
            mock_stdout.getvalue(),
            "[RUN] arg1 arg2a arg2b arg3\n[RUN async] arg1 arg2a arg2b arg3\n",
        )
        # TODO: Add quotes for arguments with spaces like in _shell_cmd()

    def test_shell_cmd(self):
        """test shell_cmd"""
        args = ["arg1", "arg2a arg2b", "arg3"]
        env = {"key1": "value1", "key2": "value2"}
        self.assertEqual(
            _shell_cmd(args, env),
            'key1="value1" key2="value2" arg1 "arg2a arg2b" arg3',
        )

    def test_print_file_shell_cmd(self):
        """test print_file_shell_cmd"""
        args = ["arg1", "arg2a arg2b", "arg3"]
        env = {"key1": "value1", "key2": "value2"}
        curdir = "directory"
        tmpdir = tempfile.mkdtemp(prefix="test-benchkit-")
        tmppath = os.path.join(tmpdir, "tmp")
        _print_file_shell_cmd(args, curdir, env, tmppath)
        with open(tmppath, "r") as file:
            contents = file.read()
        shutil.rmtree(tmpdir)
        self.assertEqual(
            contents,
            "#!/bin/sh\n"
            "set -e\n"
            "\n"
            f"cd {curdir}\n"
            'key1="value1" key2="value2" arg1 "arg2a arg2b" arg3\n',
        )
        # TODO: Why not use real_curdir?

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_shell_cmd(self, mock_stdout):
        """test print_shell_cmd"""
        args = ["arg1", "arg2a arg2b", "arg3"]
        env = {"key1": "value1", "key2": "value2"}
        curdir = "directory"
        real_curdir = os.path.join(os.getcwd(), curdir)
        _print_shell_cmd(args, curdir, env, None)
        _print_shell_cmd(args, None, env, None)
        self.assertEqual(
            mock_stdout.getvalue(),
            "[SHELL] To run in shell:\n"
            f"  cd {real_curdir}\n"
            '  key1="value1" key2="value2" arg1 "arg2a arg2b" arg3\n'
            "[SHELL] To run in shell:\n"
            '  key1="value1" key2="value2" arg1 "arg2a arg2b" arg3\n',
        )

    def test_get_process_nb_threads(self):
        """test get_process_nb_threads"""
        # TODO: Function should raise exception if process is finished
        with subprocess.Popen(["python3", "-c", "for _ in range(10**7): pass"]) as proc:
            comm = LocalCommLayer()
            threads = comm.get_process_nb_threads(process_handle=proc)
            self.assertEqual(1, threads)
            proc.wait()
            # TODO: Run some program that generates more threads

    def test_get_process_status(self):
        """test get_process_status"""
        # TODO: Function should raise exception if process is finished
        with subprocess.Popen(["python3", "-c", "for _ in range(10**7): pass"]) as proc:
            time.sleep(0.1)
            comm = LocalCommLayer()
            status = comm.get_process_status(process_handle=proc)
            self.assertEqual("R", status)
            proc.wait()

    @patch("sys.stdout", new_callable=StringIO)
    def test_shell_out(self, mock_stdout):
        """test shell_out"""
        args = ["python3", "-c", "x = int(input()); print(x**2)"]
        stdin = "4"
        out = shell_out(args, stdin)

        self.assertEqual(out, "16\n")
        self.assertEqual(
            mock_stdout.getvalue(),
            "[RUN] python3 -c x = int(input()); print(x**2)\n[OUT]\n16\n",
        )

    def test_shell_interactive(self):
        """test shell_interactive"""
        # TODO

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_header(self, mock_stdout):
        """test print_header"""
        # TODO: Why argument print_input prints command arguments?
