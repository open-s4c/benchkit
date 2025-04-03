# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT


from __future__ import annotations

import shlex
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from benchkit.communication import CommunicationLayer
from benchkit.shell.args import Arg, ExecutableArg, StrArg


class Command(ABC):
    @abstractmethod
    def accept(self, visitor):
        pass

    def run_with(
        self,
        comm_layer: CommunicationLayer,
    ) -> str:
        return run_command(
            command=self,
            comm_layer=comm_layer,
        )

    def resolve(self, comm_layer: CommunicationLayer) -> Command:
        from benchkit.shell.visitors.command_visitor import CommandResolver

        return self.accept(visitor=CommandResolver(comm_layer=comm_layer))


@dataclass
class SingleCommand(Command):
    program: Arg
    args: List[Arg]

    def accept(self, visitor):
        return visitor.visit_single_command(self)

    def to_list_str(self) -> List[str]:
        from benchkit.shell.visitors.arg_visitor import ArgStringifier

        arg_str = ArgStringifier()
        argv0 = str(self.program.accept(arg_str))
        argvn = [str(arg.accept(arg_str)) for arg in self.args]
        command_lst = [argv0] + argvn
        return command_lst

    def to_str(self) -> str:
        command_lst = self.to_list_str()
        command_str = " ".join(command_lst)
        return command_str


class WhichCommand(SingleCommand):
    def __init__(self, name: str):
        super().__init__(program=ExecutableArg("which"), args=[StrArg(name)])


@dataclass
class SequenceCommand(Command):
    commands: List[Command]

    def accept(self, visitor):
        return visitor.visit_sequence_command(self)

def run_command(
    command: Command,
    comm_layer: CommunicationLayer,
) -> str:
    # TODO return
    from benchkit.shell.visitors.command_visitor import CommandExecutor

    executor = CommandExecutor(comm_layer=comm_layer)
    return executor.run(command=command)


def command_from_liststr(command: List[str]) -> SingleCommand:
    if len(command) == 0:
        raise ValueError(
            "Empty command. There must be at least one argument, the program name or path."
        )

    return SingleCommand(
        program=ExecutableArg(name=command[0]),
        args=[StrArg(string=a) for a in command[1:]],
    )


def command_from_str(command: str) -> SingleCommand:
    shlexed_command = shlex.split(command)
    return command_from_liststr(command=shlexed_command)
