# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Interactions with asynchronous shells.
"""

import os
import signal
import subprocess
import sys
from typing import Optional

from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.utils import get_args, print_header
from benchkit.utils.types import Command, Environment, PathType, SplitCommand


class AsyncProcess:
    """
    Handle for asynchronous process.
    """

    class AsyncProcessError(Exception):
        """Errors with asynchronous processes."""

        def __init__(self, msg: str, returncode: int):
            super().__init__(msg)
            self.returncode = returncode

    def __init__(
        self,
        platform: Platform,
        arguments: SplitCommand,
        stdout_path: PathType,
        stderr_path: PathType,
        current_dir: Optional[PathType] = None,
        environment: Environment = None,
    ):
        self._platform = platform
        self._arguments = arguments
        self._stderr_path = stderr_path
        self._stdout_path = stdout_path

        self._stderr_handle = open(stderr_path, "w")
        self._stdout_handle = open(stdout_path, "w")
        self._error_code = None

        self._process = self._platform.comm.background_subprocess(
            arguments,
            stdout=self._stdout_handle,
            stderr=self._stderr_handle,
            cwd=current_dir,
            env=environment,
            establish_new_connection=True,
        )

    @property
    def pid(self):
        """
        Get the process ID of the process.

        Returns:
            _type_: the process ID of the process.
        """
        return self._process.pid

    @property
    def command(self) -> str:
        """
        Get the original command ran to create the process.

        Returns:
            str: the original command ran to create the process.
        """
        return " ".join(self._arguments)

    def send_signal(
        self,
        signal_code: int,
        pid: int,  # TODO why isn't it this automated?
    ) -> None:
        """
        Send a signal to the asynchronous process.

        Args:
            signal_code (int): code of the signal to send.
            pid (int): pid of the remote process to send a signal too.
        """
        if self._platform.comm.is_local:
            self._process.send_signal(signal_code)
        else:
            self._platform.comm.signal(pid=pid, signal_code=signal_code)

    def wait(self, timeout: Optional[int] = None) -> None:
        """
        Wait for the process to complete (synchronously then), possibly with timeout.

        Args:
            timeout (Optional[int], optional):
                if not None, number of seconds to wait before timing out.
                Defaults to None.

        Raises:
            AsyncProcess.AsyncProcessError: if the process ended with a non-zero exit code.
        """
        self._process.wait(timeout=timeout)
        self._error_code = self._process.returncode

        if not self._stdout_handle.closed:
            self._stdout_handle.flush()
        if not self._stderr_handle.closed:
            self._stderr_handle.flush()

        self._stdout_handle.close()
        self._stderr_handle.close()

        if 0 != self._error_code:
            _flush()
            print(self._error(), file=sys.stderr)
            _flush()
            raise AsyncProcess.AsyncProcessError(
                msg=f'Error code {self._error_code} returned by command "{self.command}"',
                returncode=self._error_code,
            )

    def find_matching_ssh(self, local_pid):
        line = get_current_platform().comm.pipe_shell(
            command=f"netstat -tp | grep {local_pid}" + " | awk '{print $4}'",
            print_command = False,
        )
        port = line.split(':')[-1].split('\n')[0]

        line = self._platform.comm.pipe_shell(
            command=f"sudo netstat -tp | grep {port}" + " | awk '{print $7}'",
            print_command = False,
        )

        remote_pid = line.split('/')[0].split('\n')[0]

        return remote_pid

    def kill_remote_process_hierarchy(self, remote_pid):

        children = self._platform.comm.pipe_shell(
            command=f"ps -o pid= --ppid {remote_pid}",
            print_command = False,
            ignore_ret_codes = [1],
        )

        if children != "":

            children = children.strip().split(' ')

            for child in children:
                self.kill_remote_process_hierarchy(child)

        self._platform.comm.pipe_shell(
            command=f"sudo kill {remote_pid}",
            print_command = False,
            ignore_ret_codes = [1],
        )


    def stop(self) -> None:
        """
        Stop a running asynchronous process.

        Raises:
            AsyncProcess.AsyncProcessError: if the process was already completed.
        """
        try:
            self.wait(timeout=1)
            rcode = self._process.returncode
            if rcode is not None:
                raise AsyncProcess.AsyncProcessError(
                    msg=f"Cannot kill: async process already completed execution with code {rcode}",
                    returncode=rcode,
                )
        except subprocess.TimeoutExpired:
            pass

        # Kill assynchronous process and all processes on the same group id
        # As we create a new group id for each background process, this will kill its children

        # If using a remote call, kill the remote process
        if self._platform.comm.remote_host is not None:
            remote_pid = self.find_matching_ssh(self._process.pid)
            self.kill_remote_process_hierarchy(remote_pid)

        os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
        self._process.wait()

    def output(self) -> str:
        """
        Return the output of the process, possibly waiting for its completion.

        Returns:
            str: the output of the process, possibly waiting for its completion.
        """
        self.wait()
        with open(self._stdout_path, "r") as stdout_file:
            output = stdout_file.read()
        return output

    def is_finished(self) -> bool:
        """
        Return whether the asynchronous process has finished its execution.

        Returns:
            bool: whether the asynchronous process has finished its execution.
        """
        finished = True
        try:
            self._process.wait(timeout=0)
        except subprocess.TimeoutExpired:
            finished = False
        return finished

    def _error(self) -> str:
        with open(self._stderr_path, "r") as stderr_file:
            output = stderr_file.read()
        return output


def shell_async(
    command: Command,
    stdout_path: PathType,
    stderr_path: PathType,
    platform: Platform,
    current_dir: Optional[PathType] = None,
    environment: Environment = None,
    print_input: bool = True,
    print_env: bool = True,
    print_curdir: bool = True,
    print_shell_cmd: bool = False,
    print_file_shell_cmd: bool = True,
) -> AsyncProcess:
    """
    Start an asynchronous shell command.

    Args:
        command (Command):
            the command to run.
        stdout_path (PathType):
            path where to write the file that will contain the stdout of the command.
        stderr_path (PathType):
            path where to write the file that will contain the stderr of the command.
        platform (Platform):
            platform where to run the shell command.
        current_dir (Optional[PathType], optional):
            directory where to run the command. If None, the current directory is used.
            Defaults to None.
        environment (Environment, optional):
            environment variables to pass to the command.
            Defaults to None.
        print_input (bool, optional):
            whether to print the command. TODO should be renamed "print_command"
            Defaults to True.
        print_env (bool, optional):
            whether to print the environment variables when they are defined.
            Defaults to True.
        print_curdir (bool, optional):
            whether to print the current directory if provided.
            Defaults to True.
        print_shell_cmd (bool, optional):
            whether to print the complete shell command, ready to be copy-pasted in a terminal.
            Defaults to False.
        print_file_shell_cmd (bool, optional):
            whether to print the shell command in a log file (`/tmp/benchkit.sh`).
            Defaults to True.

    Returns:
        AsyncProcess: the handle of the newly created asynchronous process.
    """
    arguments = get_args(command)

    print_header(
        arguments=arguments,
        current_dir=current_dir,
        environment=environment,
        print_input=print_input,
        print_env=print_env,
        print_curdir=print_curdir,
        print_shell_cmd=print_shell_cmd,
        print_file_shell_cmd=print_file_shell_cmd,
        asynced=True,
        remote_host=platform.comm.remote_host,
    )

    process = AsyncProcess(
        platform=platform,
        arguments=arguments,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        current_dir=current_dir,
        environment=environment,
    )

    return process


def _flush() -> None:
    sys.stdout.flush()
    sys.stderr.flush()
