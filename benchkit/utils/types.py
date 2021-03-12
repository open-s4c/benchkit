# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Useful types across the whole benchkit codebase.
"""

import os
import pathlib
from typing import Any, Dict, Iterable, List

CpuOrder = None | str | Iterable[int]

PathType = pathlib.Path | os.PathLike | str

SplitCommand = List[str]
Command = str | SplitCommand

LdPreloadLibraries = List[PathType]
EnvironmentVariables = Dict[str, str]
Environment = None | EnvironmentVariables

VariableName = str
UglyValue = Any
PrettyValue = str
UglyToPrettyMapping = Dict[UglyValue, PrettyValue]
Pretty = Dict[VariableName, UglyToPrettyMapping]
Constants = None | Dict[str, Any]
