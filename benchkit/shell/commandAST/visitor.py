# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

import shlex
from typing import Dict

from benchkit.shell.commandAST.abstractTypes import Node
from benchkit.shell.commandAST.command import command
from benchkit.shell.commandAST.nodes.commandNodes import CommandNode, InlineCommandNode, StringNode
from benchkit.shell.commandAST.nodes.variable_node import (
    Visitor,
)
from benchkit.shell.commandAST.Visitors.print_visitor import printASTVisitor
from benchkit.shell.commandAST.Visitors.variable_visitors import (
    VariableFinder,
    resolveAllVariables,
)
from benchkit.shell.commandAST.Visitors.verification_visitors import (
    OnlyStringAndCommandNodesChecker,
)


def VariableDuplicateDetector(ast: Node):
    variable_finder = VariableFinder()
    variable_finder.visitAST(ast)
    var_names = list(map(lambda x: x.name, variable_finder.variables))
    for var_name in var_names:
        if var_names.count(var_name) >= 2:
            raise NameError(f"The variable name {var_name} occures in two sepperate objects")


def CheckReadyForConversionToCommand(ast: CommandNode):
    # TODO: I want to make a grammar checker this will do for now
    check = OnlyStringAndCommandNodesChecker()
    ast.visit(check)


def convertComandToString(ast: CommandNode) -> str:
    class CommandToStringVisitor(Visitor):
        def visit_node(self, node: Node) -> Node:
            if isinstance(node, CommandNode):
                new_arg_list = []
                for arg in node.arguments:
                    if isinstance(arg, InlineCommandNode):
                        converted_ast = arg.visit(converter)
                        new_arg_list.append(converted_ast.command)
                        new_arg_list += converted_ast.arguments
                    else:
                        new_arg_list.append(arg)
                    node.arguments = new_arg_list
                return StringNode(convertComandToString(node))
            return node.visit(self)

    converter = CommandToStringVisitor()
    converted_ast = ast.visit(converter)

    args = [x.argument for x in converted_ast.arguments]
    args.insert(0, converted_ast.command.argument)
    print(args)
    return shlex.join(args)


# Functions to hide away visitors
def printAst(ast: Node):
    v = printASTVisitor()
    v.visitAST(ast)


def resolveAllVariablesWithDict(ast: Node, d: Dict[str, str]):
    variable_resolver = resolveAllVariables(d)
    # check if amountOfTimeToSleep is not used twice in the command
    # by dfferent vars resulting in wrong assignment possibly
    VariableDuplicateDetector(ast)

    # Resolve the vars given an assignment dictionairy
    return variable_resolver.visitAST(ast)


def getString(ast: Node):

    # Make sure that the command has been sufficiently resolved by visitors
    # aka there are no leftovers from bad patterns
    CheckReadyForConversionToCommand(ast)

    # Convert the ast to a string and print it
    return convertComandToString(ast)


def execute_on_remote(ast: Node, host: str, port: int) -> Node:
    return command("ssh", [host, "-p", str(port), "-t", ast])


def inline(ast: CommandNode) -> InlineCommandNode:
    return InlineCommandNode(ast.command, ast.arguments)
