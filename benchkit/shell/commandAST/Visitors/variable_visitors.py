# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from typing import Dict, Set

from benchkit.shell.commandAST.abstractTypes import Node, Visitor
from benchkit.shell.commandAST.nodes.commandNodes import StringNode
from benchkit.shell.commandAST.nodes.variable_node import Var


class resolveAllVariables(Visitor):
    def __init__(self, assignment: Dict[str, str]) -> None:
        self.assignment = assignment

    def visit_node(self, node: Node) -> Node:
        if isinstance(node, Var):
            if node.name in self.assignment:
                return StringNode(self.assignment[node.name])
            else:
                raise ValueError(
                    f"resolveAllVariables needs a value for all var nodes."
                    f"Var node with name {node.name} has no assigned value"
                )
        return node.visit(self)


class VariableFinder(Visitor):
    def __init__(self) -> None:
        self.variables: Set[Var] = set()

    def visit_node(self, node: Node) -> Node:
        if isinstance(node, Var):
            self.variables.add(node)
        node.visit(self)
        return node
