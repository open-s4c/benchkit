"""
Command wrapper for the "valgrind" utility. 
Simply collects heap usage of a program.
"""

import os.path
from typing import List


from functools import cache
from benchkit.commandwrappers import CommandWrapper, PackageDependency
from benchkit.utils.types import PathType
from benchkit.commandwrappers.perf import _which


@cache
def _valgrind_prefix():
    return _which("valgrind")


class ValgrindWrapper(CommandWrapper):
    """ Basic command wrapper for the "valgrind" utility """

    tools = []
    def __init__(self,
                tool: str = None,
                 output_file: str = "valgrind-out.txt") -> None:
        super().__init__()
        self.output_file = output_file
        # Add extra tools here
        # No tools supported yet, need to deal with different output files
        if not tool in self.tools and tool is not None:
            raise ValueError(f"Tool: {tool} not supported. Supported tools: {self.tools}")
        else: self.tool = tool

    @classmethod
    def get_supported_tools(cls) -> List[str]:
        """
        Get the list of supported tools for valgrind.
        At this point only the basic functionalities of valgrind are supported.


        Returns:
            List[str]: currently supported tools.
        """

        return cls.tools

    def command_prefix(self,
                       record_data_dir: PathType = None,
                       **_kwargs) -> List[str]:
        """
        Creates the Valgrind command prefix.

        """
        valgrind_exec = _valgrind_prefix()
        tool_prefix = []
        output_path = os.path.join(record_data_dir,self.output_file)
        if self.tool is not None:
            tool_prefix = [f"--tool={self.tool}"]
        output_option = [f"--log-file={output_path}"]
        return [valgrind_exec] + tool_prefix + output_option

    def dependencies(self) -> List[PackageDependency]:
        """Dependencies of the command wrapper.

        Returns:
            List[PackageDependency]: list of dependencies.
        """
        return [PackageDependency("valgrind")]
