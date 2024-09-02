#!/usr/bin/env python3
# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import subprocess
from typing import Iterable

from pythainer.runners import ConcreteDockerRunner

from benchkit.communication import CommunicationLayer
from benchkit.communication.utils import command_with_env, remote_shell_command
from benchkit.shell.shell import shell_out
from benchkit.utils.types import Command, Environment, PathType, SplitCommand


class DockerCommLayer(CommunicationLayer):
    """Communication layer to handle a container host through Docker."""

    def __init__(
        self,
        docker_runner: ConcreteDockerRunner,
        environment: Environment = None,
    ):
        super().__init__()
        self._docker_runner = docker_runner
        self._additional_environment = environment if environment is not None else {}
        self._command_prefix = None

    @property
    def remote_host(self) -> str | None:
        return None

    @property
    def is_local(self) -> bool:
        return True  # TODO temporarily to avoid implementing copy_to_host

    def _get_command_prefix(self) -> SplitCommand:
        if self._command_prefix is None:
            self._command_prefix = self._docker_runner.get_command()[:-1]
        return self._command_prefix

    def background_subprocess(
        self,
        command: Command,
        stdout: PathType,
        stderr: PathType,
        cwd: PathType | None,
        env: dict | None,
        establish_new_connection: bool=False
    ) -> subprocess.Popen:
        # TODO This is a solution that's a bit dangerous, as the user would commonly expect the
        # background process to run inside the docker container. We should keep this use case
        # in mind when revamping the shell commands, and perhaps refactor this code again.
        print("[WARNING] Potentially unexpected behaviour of docker background subprocess method")

        env_command = command_with_env(
            command=command,
            environment=env,
            additional_environment=self._additional_environment,
        )
        full_command = self._remote_shell_command(
            remote_command=env_command,
            remote_current_dir=cwd
        )

        return subprocess.Popen(
            full_command,
            stdout=stdout,
            stderr=stderr,
            env=env,
            preexec_fn=None
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
        )

        return output

    def get_process_nb_threads(self, process_handle: subprocess.Popen) -> int:
        raise NotImplementedError("TODO")

    def get_process_status(self, process_handle: subprocess.Popen) -> str:
        raise NotImplementedError("TODO")

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

    def _remote_shell_command(
        self,
        remote_command: Command,
        remote_current_dir: PathType | None = None,
    ) -> SplitCommand:
        remote_command = remote_shell_command(
            remote_command=remote_command,
            remote_current_dir=remote_current_dir,
        )

        full_command = self._get_command_prefix() + [
            "bash",
            "-c",
            remote_command,
        ]  # TODO maybe cleaner split in the future

        return full_command
