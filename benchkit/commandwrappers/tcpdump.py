import os
import socket
from typing import List, Optional

from benchkit.commandwrappers import CommandWrapper
from benchkit.dependencies.packages import PackageDependency
from benchkit.utils.types import PathType


class TcpdumpWrap(CommandWrapper):
    """Command wrapper for the `tcpdump` utility."""

    def __init__(
        self,
        interface: str = "",
        count_packets: int = 0,
        filter_expression: str = "",
        read_from_file: str = "",
        show_timestamp: bool = False,
        verbose_output: bool = False,
        write_to_file: str = "",
        snapshot_length: int = 0,
        no_promiscuous_mode: bool = False,
        display_packet_data: bool = False,
    ):
        super().__init__()

        self._interface = interface
        self._count_packets = count_packets
        self._filter_expression = filter_expression
        self._read_from_file = read_from_file
        self._show_timestamp = show_timestamp
        self._verbose_output = verbose_output
        self._write_to_file = write_to_file
        self._snapshot_length = snapshot_length
        self._no_promiscuous_mode = no_promiscuous_mode
        self._display_packet_data = display_packet_data

    def dependencies(self) -> List[PackageDependency]:
        return super().dependencies() + [
            PackageDependency("tcpdump"),
        ]

    def _check_socket_access(self, port: int) -> bool:
        try:
            # Attempt to create a socket listening on localhost
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return True
        except OSError:
            return False

    def command_prefix(
        self,
        record_data_dir: Optional[PathType],
        **kwargs,
    ) -> List[str]:
        cmd_prefix = super().command_prefix(**kwargs)

        if record_data_dir is None:
            raise ValueError(
                "Record data directory cannot be None, it is required to save tcpdump output."
            )

        # Check if user has access to the socket
        if not self._check_socket_access(80):
            raise PermissionError("You do not have access to the socket.")

        tcpdump_output_pathname = os.path.join(record_data_dir, "tcpdump.pcap")

        options = ["tcpdump"]
        if self._interface:
            options.extend(["-i", self._interface])

        if self._count_packets > 0:
            options.extend(["-c", str(self._count_packets)])

        if self._filter_expression:
            options.append(self._filter_expression)

        if self._read_from_file:
            options.extend(["-r", self._read_from_file])

        if self._show_timestamp:
            options.append("-tt")

        if self._verbose_output:
            options.append("-v")

        options.extend(["-w", tcpdump_output_pathname])

        if self._snapshot_length > 0:
            options.extend(["-s", str(self._snapshot_length)])

        if self._no_promiscuous_mode:
            options.append("-p")

        if self._display_packet_data:
            options.append("-X")

        options.append("&")  # Run tcpdump in the background
        cmd_prefix += options

        return cmd_prefix

