# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to handle communication between the host running the benchkit and the target that needs to
run the benchmark.
In some cases, these two are the same, when running locally.
In other case, the target is a remote host reachable with some communication protocols (e.g. SSH).
The right instance of `CommunicationLayer` will transparently execute the machine/OS operations,
while the client code can remain the same for any scenario.
"""

import os
import os.path
import pathlib
import subprocess
import getpass
from shutil import which
from benchkit.shell.shell import pipe_shell_out, shell_out
from typing import Iterable, Dict, List, Optional
from functools import lru_cache

from benchkit.communication.utils import (
    command_with_env,
    format_arg,
    remote_shell_command,
)
from benchkit.utils.types import Command, Environment, PathType, SplitCommand


class CommunicationLayer:
    """Base class for any communication layer."""

    def __init__(self):
        pass

    @property
    def remote_host(self) -> str | None:
        """Returns an identifier (typically hostname) of the remote host, or None if communication
        happens locally.

        Returns:
            str | None: name of the remote host or None if communication happens locally.
        """
        raise NotImplementedError()

    @property
    def is_local(self) -> bool:
        """Returns whether the communication layer happens locally on the host.

        Returns:
            bool: whether the communication layer happens locally on the host.
        """
        raise NotImplementedError()

    def pipe_shell(
        self,
        command: Command,
        current_dir: Optional[PathType] = None,
        shell: bool = False,
        ignore_ret_codes: Iterable[int] = (),
    ):
        raise NotImplementedError()

    def shell(
        self,
        command: Command,
        std_input: str | None = None,
        current_dir: PathType | None = None,
        environment: Environment = None,
        shell: bool = False,
        print_input: bool = True,
        print_output: bool = True,
        print_curdir: bool = True,
        timeout: int | None = None,
        output_is_log: bool = False,
        ignore_ret_codes: Iterable[int] = (),
        ignore_any_error_code: bool = False,
    ) -> str:
        """Run a shell command on the target host.

        Args:
            command (Command):
                command to run on the target host.
            std_input (str | None, optional):
                input to pipe into the command to run, None if there is no input to provide.
                Defaults to None.
            current_dir (PathType | None, optional):
                directory where to run the command. Defaults to None.
            environment (Environment, optional):
                environment to pass to the command to run. Defaults to None.
            shell (bool, optional):
                whether a shell must be created to run the command. Defaults to False.
            print_input (bool, optional):
                whether to print the command on benchkit logs. Defaults to True.
            print_output (bool, optional):
                whether to print the command output on benchkit logs. Defaults to True.
            print_curdir (bool, optional):
                whether to print the current directoru on benchkit logs. Defaults to True.
            timeout (int | None, optional):
                number of seconds to wait for the command to complete, or None for no timeout.
                Defaults to None.
            output_is_log (bool, optional):
                whether the output of the command is expected to be logging (e.g. when running
                `cmake`). If it is the case, the logging will be printed in a `tail -f` fashion.
                Defaults to False.
            ignore_ret_codes (Iterable[int], optional):
                List of error code to ignore if it is the return code of the command.
                Defaults to () (empty collection).
            ignore_any_error_code (bool, optional):
                whether to error any error code returned by the command.

        Returns:
            str: the output of the command.
        """
        raise NotImplementedError()

    def shell_succeed(
        self,
        command: Command,
        std_input: str | None = None,
        current_dir: PathType | None = None,
        environment: Environment = None,
        shell: bool = False,
        print_input: bool = True,
        print_output: bool = True,
        print_curdir: bool = True,
        timeout: int | None = None,
        output_is_log: bool = False,
        ignore_ret_codes: Iterable[int] = (),
    ) -> bool:
        """Executes a command and return whether it succeeded without error.

        Args:
            command (Command):
                command to run on the target host.
            std_input (str | None, optional):
                input to pipe into the command to run, None if there is no input to provide.
                Defaults to None.
            current_dir (PathType | None, optional):
                directory where to run the command. Defaults to None.
            environment (Environment, optional):
                environment to pass to the command to run. Defaults to None.
            shell (bool, optional):
                whether a shell must be created to run the command. Defaults to False.
            print_input (bool, optional):
                whether to print the command on benchkit logs. Defaults to True.
            print_output (bool, optional):
                whether to print the command output on benchkit logs. Defaults to True.
            print_curdir (bool, optional):
                whether to print the current directoru on benchkit logs. Defaults to True.
            timeout (int | None, optional):
                number of seconds to wait for the command to complete, or None for no timeout.
                Defaults to None.
            output_is_log (bool, optional):
                whether the output of the command is expected to be logging (e.g. when running
                `cmake`). If it is the case, the logging will be printed in a `tail -f` fashion.
                Defaults to False.
            ignore_ret_codes (Iterable[int], optional):
                List of error code to ignore if it is the return code of the command.
                Defaults to () (empty collection).

        Returns:
            bool: whether the executed command succeeded without error.
        """
        succeed = True
        try:
            self.shell(
                command=command,
                std_input=std_input,
                current_dir=current_dir,
                environment=environment,
                shell=shell,
                print_input=print_input,
                print_output=print_output,
                print_curdir=print_curdir,
                timeout=timeout,
                output_is_log=output_is_log,
                ignore_ret_codes=ignore_ret_codes,
            )
        except subprocess.CalledProcessError:
            succeed = False
        return succeed

    def background_subprocess(
        self,
        command: Command,
        stdout: PathType,
        stderr: PathType,
        cwd: PathType | None,
        env: dict | None,
        establish_new_connection: bool = False,
    ) -> subprocess.Popen:
        """Start a background process with the provided command.

        Args:
            command (Command):
                background command to run on the target host.
            stdout (PathType):
                path to the file where to write the stdout output of the background process.
            stderr (PathType):
                path to the file where to write the stderr output of the background process.
            cwd (PathType | None):
                working directory of the background command to run.
            env (dict | None):
                environment variables to pass to the command to run.

        Returns:
            subprocess.Popen: the process handle from the subprocess module.
        """
        raise NotImplementedError()

    def signal(
        self,
        pid: int,
        signal_code: int,
    ) -> None:
        """Send a signal to the given process.

        Args:
            pid (int): pid of the process to send the signal to.
            signal_code (int): code of the signal to send.
        """
        self.shell(command=f"kill -{signal_code} {pid}")

    def get_process_nb_threads(
        self,
        process_handle: subprocess.Popen,
    ) -> int:
        """get number of threads of the given process.

        Args:
            process_handle (subprocess.Popen): process to query.

        Returns:
            int: _description_
        """
        raise NotImplementedError(
            "TODO not implemented on remote: we need the pid of the remote process... "
            "(I don't know how to do it now)"
        )

    def get_process_status(
        self,
        process_handle: subprocess.Popen,
    ) -> str:
        """get status of the given process.

        Args:
            process_handle (subprocess.Popen): process to query.

        Returns:
            str: status of the given process.
        """
        raise NotImplementedError(
            "TODO not implemented on remote: we need the pid of the remote process... "
            "(I don't know how to do it now)"
        )

    def path_exists(
        self,
        path: PathType,
    ) -> bool:
        """Whether the given path exist on the target host.

        Args:
            path (PathType): path to check existence.

        Returns:
            bool: whether the given path exist on the target host.
        """
        raise NotImplementedError()

    def read_file(
        self,
        path: PathType,
    ) -> str:
        """Read content of given filename on target host.
        Communication-aware equivalent of `file.read()`.

        Args:
            path (PathType): path of the file to read on the target host.

        Returns:
            str: content of the file.
        """
        raise NotImplementedError()

    def write_content_to_file(
        self,
        content: str,
        output_filename: PathType,
        privileged: bool = False,
    ) -> None:
        """Write given content on the given file on the target host.
        Communication-aware equivalent of `file.write()`.

        Args:
            content (str): content of the file to write.
            output_filename (PathType): path of the file where to write the content on the target
                                        host.
            privileged (bool, optional): whether the write operation needs to be root.
                                         Defaults to False.
        """
        raise NotImplementedError()

    def append_line_to_file(
        self,
        line: str,
        output_filename: PathType,
        privileged: bool = False,
    ) -> None:
        """Append given line on the given file on the target host.

        Args:
            line (str): line to append.
            output_filename (PathType): path of the file where to append the content on the target
                                        host.
            privileged (bool, optional): whether the write operation needs to be root.
                                         Defaults to False.
        """
        raise NotImplementedError

    def copy_from_host(self, source: PathType, destination: PathType) -> None:
        """Copy a file from the host (the machine benchkit is run on), to the
           target machine the benchmark will be performed on.

        Args:
            source (PathType): The source path where the file or folder is stored.
            destination: (PathType): The destination path where the file has to be
                                     copied to on the remote.
        """
        raise NotImplementedError("Copy from host is not implemented for this communication layer")

    def copy_to_host(self, source: PathType, destination: PathType) -> None:
        """Copy a file to the host (the machine benchkit is run on), from the
           target machine the benchmark will be performed on.

        Args:
            source (PathType): The source path where the file or folder is stored on the remote.
            destination: (PathType): The destination path where the file has to be
                                     copied to on the host.
        """
        raise NotImplementedError("Copy to host is not implemented for this communication layer")

    def hostname(self) -> str:
        """Get hostname of the target host.

        Returns:
            str: hostname of the target host.
        """
        result = self.shell(
            command="hostname",
            print_input=False,
            print_output=False,
        ).strip()
        return result

    def current_user(self) -> str:
        """Get current user in the target host.

        Returns:
            str: current user in the target host.
        """
        result = self.shell(
            command="whoami",
            print_input=False,
            print_output=False,
        ).strip()
        return result

    def realpath(self, path: PathType) -> pathlib.Path:
        """Get real path, following symlinks, of the given path.
        Communication aware equivalent of path.resolve().

        Args:
            path (PathType): path on the host to get.

        Returns:
            pathlib.Path: absolute and real path.
        """
        output = self.shell(
            command=f"readlink -fm {path}",
            print_input=False,
            print_output=False,
        ).strip()
        result = pathlib.Path(output)
        return result

    def isfile(self, path: PathType) -> bool:
        """Return whether the given path is a file on the target host.
        Communication-aware equivalent of `path.is_file()`.

        Args:
            path (PathType): path to the given file to check.

        Returns:
            bool: whether the given path is a file on the target host.
        """
        return self._bracket_test(path=path, opt="-f")

    def makedirs(self, path: PathType, exist_ok: bool) -> None:
        """Create a directory on the target host, with all the path leading to it.
        Communication-aware equivalent of `mkdir -p /path1/path2/path3`.

        Args:
            path (PathType): path of the new directory to create on the target host.
            exist_ok (bool): whether to ignore the fact that directory might already exist.
        """
        exist_opt = " -p " if exist_ok else ""
        self.shell(
            command=f"mkdir{exist_opt} {path}",
            print_input=False,
            print_output=False,
        )
    
    def remove(self, path: PathType, recursive: bool) -> None:
        """Remove a file or directory on the target host.

        Args:
            path (PathType): path of file or directory that needs to be removed on the target host.
            recursive (bool): whether to recursively delete everything in this path.
        """
        command = ["rm"] + (["-r"] if recursive else []) + [str(path)]
        self.shell(
            command=command,
            print_input=False,
            print_output=False,
        )

    def isdir(self, path: PathType) -> bool:
        """Return whether the given path is a file on the target host.
        Communication-aware equivalent of `path.is_dir()`.

        Args:
            path (PathType): path to the given directory to check.

        Returns:
            bool: whether the given path is a directory on the target host.
        """
        return self._bracket_test(path=path, opt="-d")

    def which(self, cmd: str) -> pathlib.Path | None:
        """Return the absolute path of a given executable in the path.

        Args:
            cmd (str): the executable command to find.

        Returns:
            pathlib.Path | None: the absolute path to the command executable or None if the command
                                 is not found.
        """
        command = f"which {cmd}"
        which_succeed = self.shell_succeed(
            command=command,
            print_input=False,
            print_output=False,
        )

        if not which_succeed:
            return None

        path = self.shell(
            command=command,
            print_input=False,
            print_output=False,
        ).strip()

        if not path:
            return None

        result = pathlib.Path(path)
        return result

    def _bracket_test(
        self,
        path: PathType,
        opt: str,
    ) -> bool:
        succeed = True
        try:
            self.shell(command=f"[ {opt} {path} ]", print_input=False, print_output=False)
        except subprocess.CalledProcessError as cpe:
            if 1 != cpe.returncode:
                raise cpe
            succeed = False
        return succeed


class LocalCommLayer(CommunicationLayer):
    """
    Communication layer with the localhost. Usually useful when the benchmark runs on the same
    host as the benchkit itself.
    """

    def __init__(self):
        super().__init__()

    @property
    def remote_host(self) -> str | None:
        return None

    @property
    def is_local(self) -> bool:
        return True

    def pipe_shell(
        self,
        command: Command,
        current_dir: Optional[PathType] = None,
        shell: bool = True,
        print_command: bool = True,
        ignore_ret_codes: Iterable[int] = (),
    ):
        """
            Pipe_shell allows running a command with pipe (e.g., "ls | grep test").

            `shell` parameter needs to be True for local execution based on test_pipe_shell.py
        """
        return pipe_shell_out(
            command=command,
            current_dir=current_dir,
            shell=shell,
            print_command=print_command,
            ignore_ret_codes=ignore_ret_codes,
        )

    def shell(
        self,
        command: Command,
        std_input: str | None = None,
        current_dir: PathType | None = None,
        environment: Environment = None,
        shell: bool = False,
        print_input: bool = True,
        print_output: bool = True,
        print_curdir: bool = True,
        timeout: int | None = None,
        output_is_log: bool = False,
        ignore_ret_codes: Iterable[int] = (),
        ignore_any_error_code: bool = False,
    ) -> str:
        return shell_out(
            command=command,
            std_input=std_input,
            current_dir=current_dir,
            environment=environment,
            shell=shell,
            print_input=print_input,
            print_output=print_output,
            print_curdir=print_curdir,
            timeout=timeout,
            output_is_log=output_is_log,
            ignore_ret_codes=ignore_ret_codes,
            ignore_any_error_code=ignore_any_error_code,
        )

    def background_subprocess(
        self,
        command: Command,
        stdout: PathType,
        stderr: PathType,
        cwd: PathType | None,
        env: dict | None,
        establish_new_connection: bool = False,
    ) -> subprocess.Popen:
        # Create background process in its own group id using os.setsid
        # This allows to easily kill all children of this background process
        return subprocess.Popen(
            command,
            stdout=stdout,
            stderr=stderr,
            cwd=cwd,
            env=env,
            preexec_fn=os.setsid,
        )

    def get_process_nb_threads(
        self,
        process_handle: subprocess.Popen,
    ) -> int:
        pid = process_handle.pid
        with open(f"/proc/{pid}/status", "r") as status_file:
            lines = [line for line in status_file if "Threads" in line]
        assert 1 == len(lines)
        line = lines[0]
        threads_str = line.split(":")[-1].strip()
        result = int(threads_str)
        return result

    def get_process_status(
        self,
        process_handle: subprocess.Popen,
    ) -> str:
        pid = process_handle.pid
        status = shell_out(
            f"ps -q {pid} -o state --no-headers",
            print_input=False,
            print_output=False,
            print_env=False,
            print_curdir=False,
            print_file_shell_cmd=False,
        )
        return status.strip()

    def path_exists(
        self,
        path: PathType,
    ) -> bool:
        return os.path.exists(path)

    def read_file(
        self,
        path: PathType,
    ) -> str:
        with open(path, "r") as file:
            file_content = file.read()
        return file_content

    def write_content_to_file(
        self,
        content: str,
        output_filename: PathType,
        privileged: bool = False,
    ):
        if privileged:
            shell_out(f"sudo tee {output_filename}", std_input=content)
        else:
            with open(output_filename, "w") as file:
                file.write(content)

    def append_line_to_file(
        self,
        line: str,
        output_filename: PathType,
        privileged: bool = False,
    ) -> None:
        rline = line + "\n"
        if privileged:
            shell_out(f"sudo tee -a {output_filename}", std_input=rline)
        else:
            with open(output_filename, "a") as file:
                file.writelines([rline])

    def copy_from_host(self, source: PathType, destination: PathType,) -> None:
        self.shell(["rsync", "-azPv", str(source), str(destination)])

    def copy_to_host(self, source: PathType, destination: PathType,) -> None:
        self.shell(["rsync", "-azPv", str(source), str(destination)])

    def current_user(self) -> str:
        return getpass.getuser()

    def realpath(self, path: PathType) -> pathlib.Path:
        output = os.path.realpath(path)
        result = pathlib.Path(output)
        return result

    def isfile(self, path: PathType) -> bool:
        return os.path.isfile(path)

    def makedirs(self, path: PathType, exist_ok: bool) -> None:
        return os.makedirs(path, exist_ok=exist_ok)

    def isdir(self, path: PathType) -> bool:
        return os.path.isdir(path)

    def which(self, cmd: str) -> pathlib.Path | None:
        result = which(cmd=cmd)

        # If result is None, pathlib.Path will throw an error because it
        # expects bytes or string.
        if result is None:
            return None

        return pathlib.Path(result)


class SSHCommLayer(CommunicationLayer):
    """Communication layer to handle a remote host over SSH."""

    def __init__(
        self,
        host: str,
        environment: Environment,
    ):
        super().__init__()
        self._host = host
        self._additional_environment = environment if environment is not None else {}

        self._ssh_host_info = self._get_ssh_info(host=host)
        self._in_ssh_config = self._is_in_ssh_config(host=host)

    @property
    def remote_host(self) -> str | None:
        return self._host

    @property
    def is_local(self) -> bool:
        return False

    def background_subprocess(
        self,
        command: Command,
        stdout: PathType,
        stderr: PathType,
        cwd: PathType | None,
        env: dict | None,
        establish_new_connection: bool = False,
    ) -> subprocess.Popen:
        full_command = self._remote_shell_command(
            remote_command=command,
            remote_current_dir=cwd,
            establish_new_connection=establish_new_connection,
        )

        # Create background process in its own group id using os.setsid
        # This allows to easily kill all children of this background process
        return subprocess.Popen(
            full_command,
            stdout=stdout,
            stderr=stderr,
            env=env,
            preexec_fn=os.setsid,
        )

    def pipe_shell(
        self,
        command: Command,
        current_dir: Optional[PathType] = None,
        shell: bool = False,
        print_command: bool = True,
        ignore_ret_codes: Iterable[int] = (),
    ):
        """
            Pipe_shell allows running a command with pipe (e.g., "ls | grep test").

            `shell` parameter needs to be False for remote execution based on test_pipe_shell.py
        """
        full_environment = {}
        full_environment |= self._additional_environment

        remote_env_lst = [f"{k}={full_environment[k]}" for k in full_environment]
        remote_env_str = " ".join(remote_env_lst)

        if isinstance(command, str):
            env_command = f"{remote_env_str} {command}"
        else:
            env_command = remote_env_lst + command

        full_command = self._remote_shell_command(
            remote_command=env_command,
            remote_current_dir=current_dir,
        )

        output = pipe_shell_out(
            command=full_command,
            current_dir=None,
            shell=shell,
            print_command=print_command,
            ignore_ret_codes=ignore_ret_codes,
        )

        return output

    def shell(
        self,
        command: Command,
        std_input: str | None = None,
        current_dir: PathType | None = None,
        environment: Environment = None,
        shell: bool = False,
        print_input: bool = True,
        print_output: bool = True,
        print_curdir: bool = True,
        timeout: int | None = None,
        output_is_log: bool = False,
        ignore_ret_codes: Iterable[int] = (),
        ignore_any_error_code: bool = False,
    ) -> str:
        env_command = command_with_env(
            command=command,
            environment=environment,
            additional_environment=self._additional_environment,
        )
        full_command = self._remote_shell_command(
            remote_command=env_command,
            remote_current_dir=current_dir,
        )

        output = shell_out(
            command=full_command,
            std_input=std_input,
            current_dir=None,
            print_input=print_input,
            print_output=print_output,
            timeout=timeout,
            output_is_log=output_is_log,
            ignore_ret_codes=ignore_ret_codes,
            ignore_any_error_code=ignore_any_error_code,
        )

        return output

    def get_process_nb_threads(self, process_handle: subprocess.Popen) -> int:
        raise NotImplementedError("TODO")

    def get_process_status(self, process_handle: subprocess.Popen) -> str:
        """
        Add simple implementation of `get_process_status` which uses the status of the SSH process
        and not of the `async process` in order to detect its termination
        """
        pid = process_handle.pid
        status = shell_out(
            f"ps -q {pid} -o state --no-headers",
            print_input=False,
            print_output=False,
            print_env=False,
            print_curdir=False,
            print_file_shell_cmd=False,
        )
        return status.strip()

    def path_exists(self, path: PathType) -> bool:
        try:
            self.shell(command=f"[ -e {path} ]", print_input=False, print_output=False)
        except subprocess.CalledProcessError as cpe:
            if 1 == cpe.returncode:
                return False
            raise cpe
        return True

    def read_file(self, path: PathType) -> str:
        return self.shell(
            command=f"cat {path}",
            print_input=False,
            print_output=False,
        )

    def write_content_to_file(
        self,
        content: str,
        output_filename: PathType,
        privileged: bool = False,
    ):
        prefix = "sudo " if privileged else ""
        self.shell(
            command=f"{prefix}tee {output_filename}",
            std_input=content,
        )

    def append_line_to_file(
        self,
        line: str,
        output_filename: PathType,
        privileged: bool = False,
    ) -> None:
        prefix = "sudo " if privileged else ""
        self.shell(
            command=f"{prefix}tee -a {output_filename}",
            std_input=line + "\n",
        )

    def copy_from_host(self, source: PathType, destination: PathType) -> None:
        if self._in_ssh_config:
            command = ["rsync", "-azPv", str(source), f"{self._host}:{destination}"]
        else:
            user = self._ssh_host_info["user"]
            hostname = self._ssh_host_info["hostname"]
            port = self._ssh_host_info["port"]
            command = ["rsync", "-av", "--progress", "-e", f"ssh -p {port}", str(source), f"{user}@{hostname}:{destination}"]

        shell_out(command=command)

    def copy_to_host(self, source: PathType, destination: PathType) -> None:
        if self._in_ssh_config:
            command = ["rsync", "-azPv", f"{self._host}:{source}", str(destination)]
        else:
            user = self._ssh_host_info["user"]
            hostname = self._ssh_host_info["hostname"]
            port = self._ssh_host_info["port"]
            command = ["rsync", "-a", "--progress", "-e", f"ssh -p {port}", f"{user}@{hostname}:{source}", str(destination)]

        shell_out(command=command)

    def _remote_shell_command(
        self,
        remote_command: Command,
        remote_current_dir: PathType | None = None,
        establish_new_connection: bool = False,
    ) -> SplitCommand:
        remote_command = remote_shell_command(
            remote_command=remote_command,
            remote_current_dir=remote_current_dir,
        )

        full_command = [
            "ssh",
            "-oControlPath=none",
        ] if establish_new_connection else ["ssh"]

        full_command = full_command + [
            "-t",
            self._host,
            remote_command,
        ]

        return full_command

    @staticmethod
    def _get_ssh_info(host: str) -> Dict[str, str]:
        output = shell_out(command=["ssh", "-G", str(host)], print_input=False, print_output=False)
        ssh_host_info = dict([line.split(" ", maxsplit=1) for line in output.splitlines()])
        return ssh_host_info

    @staticmethod
    def _is_in_ssh_config(host: str) -> bool:
        list_hosts = SSHCommLayer._list_ssh_hosts()
        return host.strip() in list_hosts

    @staticmethod
    @lru_cache(maxsize=None)
    def _list_ssh_hosts() -> List[str]:
        if not pathlib.Path("/usr/bin/fish").is_file():
            return []
        output = shell_out(command=["/usr/bin/fish", "-c", "__fish_print_hostnames"], print_input=False, print_output=False,)
        list_hosts = [line.strip() for line in output.splitlines()]
        return list_hosts
