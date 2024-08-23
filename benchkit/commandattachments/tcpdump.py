import pathlib
from benchkit.shell.shellasync import AsyncProcess
from benchkit.platforms import get_current_platform, Platform
from benchkit.utils.types import PathType
import pathlib

class TcpDump:
    
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
        platform: Platform = None,
    ) -> None:
        self.interface = interface,
        self.count_packets = count_packets,
        self.filter_expression = filter_expression
        self.read_from_file = read_from_file
        self.show_timestamp = show_timestamp
        self.verbose_output = verbose_output
        self.write_to_file = write_to_file
        self.snapshot_length = snapshot_length
        self.no_promiscuous_mode = no_promiscuous_mode
        self.display_packet_data = display_packet_data
        self.platform = platform if platform is not None else get_current_platform()
    
    def tcpdump_attach(
        self,
        record_data_dir: PathType,
    ) -> None:
        rdd = pathlib.Path(record_data_dir)
        
        tcpdump_output_pathname = rdd / "tcpdump.pcap"
        
        command = ["tcpdump"]
        
        if self.interface:
            command.extend(["-i", self.interface])
        
        if self.count_packets > 0:
            command.extend(["-c", str(self.count_packets)])
        
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
        
        # Initialize AsyncProcess for tcpdump
        AsyncProcess(
            platform=self.platform,
            arguments=command,
            stdout_path=rdd / "tcpdump.out",
            stderr_path=rdd / "tcpdump.err",
            current_dir=rdd,
        )
