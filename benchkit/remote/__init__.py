# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Module to manage remote tmux session and complete experiments.
"""

import subprocess
import time
from typing import List

import libtmux

from benchkit.communication import SSHCommLayer
from benchkit.utils.types import PathType


class TmuxRemoteSession:
    """
    Represent a tmux session running on a remote host.
    """

    def __init__(
        self,
        user: str,
        hostname: str,
        tmux_session_name: str,
        tmux_session_dir: str,
        new_session_commands: List[str],
    ):
        self._user = user
        self._hostname = hostname

        self._server = self._server_instance()

        if self.has_session(tmux_session_name=tmux_session_name):
            session = self._server.sessions.get(name=tmux_session_name)
            self.is_new_session = False
        else:
            session = self._server.new_session(
                session_name=tmux_session_name,
                start_directory=tmux_session_dir,
            )
            self.is_new_session = True

        self._session = session
        self._window = session.attached_window
        self._pane = self._window.attached_pane

        if self.is_new_session:
            for command in new_session_commands:
                self.command_line(command)

    def has_session(self, tmux_session_name: str) -> bool:
        """
        Return whether the remote host has the given tmux session opened.

        Args:
            tmux_session_name (str): name of the session to retrieve.

        Returns:
            bool: whether the remote host has the given tmux session opened.
        """
        return self._server.has_session(tmux_session_name)

    def command_line(
        self,
        command: str,
        enter: bool = True,
    ) -> None:
        """
        Run the given command on the remote tmux session command prompt.

        Args:
            command (str):
                the command to run on the remote tmux session.
            enter (bool, optional):
                whether to hit "enter" after the command has been passed. Defaults to True.
        """
        self._pane.send_keys(command, enter=enter, suppress_history=False)

    def wait_prompt(self, sleep_interval_seconds: int = 1) -> None:
        """
        Wait to get a prompt on the remote tmux session.
        If there a command currently running (then, no prompt), it will wait, by poking the remote
        tmux session every given sleep_interval_seconds.

        Args:
            sleep_interval_seconds (int, optional):
                Interval between pokes of the remote session to check prompt. Defaults to 1.
        """
        while not self._is_prompt():
            time.sleep(sleep_interval_seconds)

    def get_status(self) -> int:
        """
        Get the status of the latest command that ran (by using echo $?).

        Returns:
            int: the status of the latest command that ran (by using echo $?).
        """
        self.command_line(r"echo \$?")
        self.wait_prompt()
        status_str = self._get_before_last_line().strip()
        status = int(status_str)
        return status

    def run_command(self, command: str) -> None:
        """
        Run the given command on the prompt of the remote tmux session.

        Args:
            command (str): the command to run on the prompt of the remote tmux session.
        """
        self.command_line(command=command, enter=True)

    def _server_instance(self) -> libtmux.Server:
        server = libtmux.Server()
        return server

    def _get_before_last_line(self) -> str:
        return self._pane.capture_pane()[-2].strip()

    def _get_last_line(self) -> str:
        lines = self._pane.capture_pane()
        if not lines:
            return ""
        return self._pane.capture_pane()[-1].strip()

    def _is_prompt(self) -> bool:
        last_line = self._get_last_line()
        machine_id = f"{self._user}@{self._hostname}" in last_line
        dollar = last_line.endswith("$")
        return machine_id and dollar


class _SSHTmuxServer:
    def __init__(self, comm_layer: SSHCommLayer) -> None:
        self._comm_layer = comm_layer
        self._session_name = "default-name"

    @property
    def attached_window(self) -> "_SSHTmuxServer":
        """
        Get the window currently attached in the tmux session.

        Returns:
            _SSHTmuxServer: the window currently attached in the tmux session.
        """
        return self

    @property
    def attached_pane(self) -> "_SSHTmuxServer":
        """
        Get the pane currently active in the window of the tmux session.

        Returns:
            _SSHTmuxServer: the pane currently active in the window of the tmux session.
        """
        return self

    @property
    def sessions(self) -> "_SSHTmuxServer":
        """
        Get the tmux sessions of the remote tmux server.

        Returns:
            _SSHTmuxServer: the tmux sessions of the remote tmux server.
        """
        return self

    def get(self, name: str) -> "_SSHTmuxServer":
        """
        Get the current tmux server and name the session with the given name.

        Args:
            name (str): name for the current session.

        Returns:
            _SSHTmuxServer: the current tmux session and name the session with the given name.
        """
        self._session_name = name
        return self

    def has_session(self, tmux_session_name: str) -> bool:
        """
        Return whether the remote server has a session active that has the given session name.

        Args:
            tmux_session_name (str): session name to find in the currently open sessions.

        Returns:
            bool: Whether the remote server has a session active that has the given session name.
        """
        try:
            self._comm_layer.shell(f"tmux has-session -t {tmux_session_name}")
        except subprocess.CalledProcessError as cpe:
            if 1 == cpe.returncode:
                return False
            raise cpe
        return True

    def new_session(
        self,
        session_name: str,
        start_directory: str,
    ) -> "_SSHTmuxServer":
        """
        Create a new session called with the given name in the given start directory.

        Args:
            session_name (str): name of the session to create.
            start_directory (str): directory where to start the session.

        Returns:
            _SSHTmuxServer: the related tmux server.
        """
        self._comm_layer.shell(
            command=f"tmux new-session -d -s {session_name} -c {start_directory}"
        )
        self._session_name = session_name
        return self

    def capture_pane(self) -> List[str]:
        """
        Capture the pane and record the terminal log.

        Returns:
            List[str]: list of lines from the terminal log of the captured pane.
        """
        output = self._comm_layer.shell(command=f"tmux capture-pane -p -t {self._session_name}")
        return output.strip().splitlines()

    def send_keys(
        self,
        command: str,
        enter: bool,
        suppress_history: bool,
    ) -> None:
        """
        Send the given command as keys to the tmux session.

        Args:
            command (str): command to send.
            enter (bool): whether to press "enter" once the command is sent.
            suppress_history (bool): whether to remove the command from the shell history.
        """
        tmux_prefix = f"tmux send-keys -t {self._session_name}"
        cmd_prefix = " " if suppress_history else ""
        self._comm_layer.shell(command=f'{tmux_prefix} "{cmd_prefix}{command}"')
        if enter:
            self._comm_layer.shell(command=f'{tmux_prefix} "C-j"')


class TmuxSSHSession(TmuxRemoteSession):
    """
    Remote tmux session over SSH.
    """

    def __init__(
        self,
        user: str,
        hostname: str,
        tmux_session_name: str,
        tmux_session_dir: PathType,
        new_session_commands: List[str],
    ):
        self._comm_layer = SSHCommLayer(
            host=hostname,
            environment=None,
        )

        super().__init__(
            user=user,
            hostname=hostname,
            tmux_session_name=tmux_session_name,
            tmux_session_dir=tmux_session_dir,
            new_session_commands=new_session_commands,
        )

    def _server_instance(self) -> _SSHTmuxServer:
        server = _SSHTmuxServer(comm_layer=self._comm_layer)
        return server
