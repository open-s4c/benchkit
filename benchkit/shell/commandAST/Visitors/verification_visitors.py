# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.shell.commandAST.abstractTypes import Node, Visitor
from benchkit.shell.commandAST.nodes.commandNodes import CommandNode, StringNode


class OnlyStringAndCommandNodesChecker(Visitor):
    def visit_node(self, node: Node) -> Node:
        if not (isinstance(node, StringNode) or isinstance(node, CommandNode)):
            raise TypeError(
                f"All nodes in the ast need to be of type StringNode or CommandNode"
                f"before the comand can be executed found node of type {type(node)}"
            )
        node.visit(self)
        return node
