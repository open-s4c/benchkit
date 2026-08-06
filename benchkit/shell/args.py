# Copyright (C) 2025 Vrije Universiteit Brussel. All rights reserved.
# SPDX-License-Identifier: MIT


from abc import ABC, abstractmethod
from dataclasses import dataclass

from benchkit.utils.types import PathType


class Arg(ABC):
    @abstractmethod
    def accept(self, visitor):
        pass


@dataclass
class StrArg(Arg):
    string: str

    def accept(self, visitor):
        return visitor.visit_str_arg(self)


@dataclass
class FilePathArg(Arg):
    path: PathType

    def accept(self, visitor):
        return visitor.visit_file_path_arg(self)


@dataclass
class ExecutableArg(Arg):
    name: PathType

    def accept(self, visitor):
        return visitor.visit_executable_arg(self)
