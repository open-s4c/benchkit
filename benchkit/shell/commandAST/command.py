# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import shlex

from benchkit.shell.commandAST.nodes.commandNodes import CommandNode, StringNode
from benchkit.shell.commandAST.nodes.futureNodes import Generic, Location
from benchkit.shell.commandAST.nodes.variable_node import Node


def process_program(program: str | Generic | Location) -> StringNode:
    if type(program) is str:
        return StringNode(program.strip())
    else:
        raise TypeError()


def process_argument(argument: str | Node) -> Node:
    if type(argument) is str:
        return StringNode(argument)
    if isinstance(argument, Node):
        return argument
    else:
        raise TypeError(f"argument is of type {type(argument)}")


def command(
    program: str | Generic | Location, arguments: list[Node | str] | None = None
) -> CommandNode:
    if arguments is None:
        arguments = []
    if isinstance(program, str):
        ls = shlex.split(program)
        program = ls[0]
        extra_argumens = ls[1::]
        arguments = extra_argumens + arguments
    if not arguments:
        return CommandNode(process_program(program), None)
    else:
        return CommandNode(process_program(program), list(map(process_argument, arguments)))
