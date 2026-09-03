# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Main benchkit module.
See README.md in the root of the repository for details.
"""

from benchkit.core.compat.new2old import CampaignCartesianProduct, CampaignIterateVariables
from benchkit.engine.execution import ExecutionEngine
from benchkit.engine.generators import (
    CartesianGenerator,
    FilteredGenerator,
    ListGenerator,
    RecordGenerator,
)
from benchkit.engine.policies import ExecutionPolicy, SequentialPolicy
from benchkit.engine.stores import CsvJsonStore, ResultStore

__all__ = [
    "CampaignCartesianProduct",
    "CampaignIterateVariables",
    "CartesianGenerator",
    "CsvJsonStore",
    "ExecutionEngine",
    "ExecutionPolicy",
    "FilteredGenerator",
    "ListGenerator",
    "RecordGenerator",
    "ResultStore",
    "SequentialPolicy",
]
