# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT


from abc import ABC, abstractmethod

from benchkit.communication import CommunicationLayer
from benchkit.shell.commands import Command, SingleCommand


class CommandVisitor(ABC):
    @abstractmethod
    def visit_single_command(self, command: SingleCommand):
        pass


class CommandResolver(CommandVisitor):
    def __init__(self, comm_layer: CommunicationLayer):
        self.comm_layer = comm_layer

    def visit_single_command(self, command: SingleCommand):
        from benchkit.shell.visitors.arg_visitor import ArgResolver

        arg_resolver = ArgResolver(self.comm_layer)
        return SingleCommand(
            program=command.program.accept(arg_resolver),
            args=[arg.accept(arg_resolver) for arg in command.args],
        )


class CommandExecutor(CommandVisitor):
    def __init__(self, comm_layer: CommunicationLayer):
        self.comm_layer = comm_layer

    def run(self, command: Command):
        return command.accept(self)

    def visit_single_command(
        self,
        command: SingleCommand,
    ):
        shlexed_cmd = command.to_list_str()
        output = self.comm_layer.shell(  # TODO Replace backend
            command=shlexed_cmd,
            current_dir=None,  # TODO
            environment=None,  # TODO
            output_is_log=False,  # TODO
        ).strip()
        return output


class CommandShellscriptor(CommandVisitor):
    def __init__(self):
        pass

    def generate_shell_script_str(self, command: Command,) -> str:
        return command.accept(self)

    def visit_single_command(self, command: SingleCommand,) -> str:
