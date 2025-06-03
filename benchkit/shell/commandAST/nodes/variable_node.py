# Copyright (C) 2024 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT

from typing import Any, List

from benchkit.shell.commandAST.abstractTypes import Node, Visitor


class Var(Node):
    """
    Class for variables that we can use to do Parameterization
    """

    def __init__(
        self,
        name: str,
        parameter_range: None | List[Any] = None,
        parameter_options: None | List[Any] = None,
    ):
        # Make it so you can not instanciate this class
        if type(self) is Var:
            raise TypeError("Can not instanciate generic variables")

        if parameter_range is None:
            parameter_range = []
        if parameter_options is None:
            parameter_options = []

        self.parameter_range = parameter_range
        self.parameter_options = parameter_options

        self.name = name
        self.id = id(self)

    def visit(self, visitor: Visitor):
        return self


class RuntimeVariable(Var):
    """Type used to designate a variable as a runtime variable
    ex: Number of threads, size of the array we want to sort"""


class BuildVariable(Var):
    """Type used to deignate a variable as a build variable
    ex: optimization level of gcc compiler,"""


class SetupVariable(Var):
    """Type used to deignate a variable as a settup time variable
    ex: variables that decide the shedular"""
