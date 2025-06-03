# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from abc import ABC, abstractmethod


class Node(ABC):
    @abstractmethod
    def visit(self, visitor: Visitor) -> Node:
        """This method defines how the different ellemts of the AST should be traversed
        Needs to implemented such that we can always traverse all nodes in a tree"""


class Visitor(ABC):
    def visit_node(self, node: Node) -> Node:
        """This method When visiting a node can do manipulations on the node
        and continue the traversal in a custom way"""
        return node.visit(self)

    def visitAST(self, node: Node) -> Node:
        return self.visit_node(node)
