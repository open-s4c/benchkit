# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT


from abc import ABC, abstractmethod
from pathlib import Path

from benchkit.shell.args import ExecutableArg, FilePathArg, StrArg


class ArgVisitor(ABC):
    @abstractmethod
    def visit_str_arg(self, arg: StrArg):
        pass

    @abstractmethod
    def visit_file_path_arg(self, arg: FilePathArg):
        pass

    @abstractmethod
    def visit_executable_arg(self, arg: ExecutableArg):
        pass


class ArgResolver(ArgVisitor):
    def __init__(self, comm):
        self.comm = comm

    def visit_str_arg(self, arg: StrArg):
        return arg

    def visit_file_path_arg(self, arg: FilePathArg):
        return FilePathArg(path=Path(arg.path).resolve())

    def visit_executable_arg(self, arg: ExecutableArg) -> ExecutableArg:
        from benchkit.shell.args import ExecutableArg
        from benchkit.shell.commands import WhichCommand

        which_cmd = WhichCommand(arg.name)
        result = which_cmd.run_with(comm_layer=self.comm)
        # TODO return ExecutableArg(name=Path(result.stdout.strip()).resolve())
        return ExecutableArg(name=Path(result.strip()).resolve())


class ArgStringifier(ArgVisitor):
    def visit_str_arg(self, arg: StrArg):
        return arg.string

    def visit_file_path_arg(self, arg: FilePathArg):
        return str(arg.path)

    def visit_executable_arg(self, arg: ExecutableArg):
        return arg.name
