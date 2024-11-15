import pathlib
from typing import List

from benchkit.benchmark import RecordResult, WriteRecordFileFunction
from benchkit.platforms import Platform, get_current_platform
from benchkit.shell.shellasync import AsyncProcess
from benchkit.utils.types import PathType


class TcpDump:

    def __init__(
        self,
        interface: str = "",
        filter_expression: str = None,
        read_from_file: str = "",
        show_timestamp: bool = False,
        verbose_output: bool = False,
        write_to_file: str = "",
        snapshot_length: int = 0,
        no_promiscuous_mode: bool = False,
        display_packet_data: bool = False,
        platform: Platform = None,
    ) -> None:
        self.interface = (interface,)
        self.filter_expression = filter_expression
        self.read_from_file = read_from_file
        self.show_timestamp = show_timestamp
        self.verbose_output = verbose_output
        self.write_to_file = write_to_file
        self.snapshot_length = snapshot_length
        self.no_promiscuous_mode = no_promiscuous_mode
        self.display_packet_data = display_packet_data
        self.process = (None,)
        self.platform = platform if platform is not None else get_current_platform()

    def attachment(
        self,
        process,
        record_data_dir: PathType,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)

        tcpdump_output_pathname = rdd / "tcpdump.pcap"

        command = ["sudo", "tcpdump"]

        if self.interface is not None:
            command.extend(["-i", self.interface])

        if self.filter_expression:
            command.append(self.filter_expression)

        if self.read_from_file:
            command.extend(["-r", self.read_from_file])

        if self.show_timestamp:
            command.append("-tt")

        if self.verbose_output:
            command.append("-v")

        command.extend(["-w", str(tcpdump_output_pathname)])

        if self.snapshot_length > 0:
            command.extend(["-s", str(self.snapshot_length)])

        if self.no_promiscuous_mode:
            command.append("-p")

        if self.display_packet_data:
            command.append("-X")

        print("Command:", command, type(command))

        # Initialize AsyncProcess for tcpdump
        self.process = AsyncProcess(
            platform=self.platform,
            arguments=command,
            stdout_path=rdd / "tcpdump.out",
            stderr_path=rdd / "tcpdump.err",
            current_dir=rdd,
        )

    def post_run_hook(
        self,
        experiment_results_lines: List[RecordResult],
        record_data_dir: PathType,
        write_record_file_fun: WriteRecordFileFunction,
    ) -> None:
        self.process._process.terminate()
