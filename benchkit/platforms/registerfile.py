# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""Register file example."""

from benchkit.platforms.servers import (
    GigabyteAMDEPYC7352c24x2,
    GigabyteIntelXeonGold5222x2,
    Huawei2288XIntelXeonGold6266Cx2,
    Taishan200Kunpeng9204826x2,
    Taishan200Kunpeng9206426x2,
)
from benchkit.platforms.workstations import (
    AMDRyzen536006C,
    HuaweiMatebookXPro,
    WorkstationIntelXeonW2133,
)

HOSTNAME_TO_PLATFORM = {
    "core": AMDRyzen536006C,
    "hlab": WorkstationIntelXeonW2133,
    "node11": Huawei2288XIntelXeonGold6266Cx2,
    "node12": GigabyteAMDEPYC7352c24x2,
    "node14": Huawei2288XIntelXeonGold6266Cx2,
    "node15": GigabyteIntelXeonGold5222x2,
    "node21": Taishan200Kunpeng9204826x2,
    "node23": Taishan200Kunpeng9204826x2,
    "node24": Taishan200Kunpeng9206426x2,
    "node25": Taishan200Kunpeng9206426x2,
    "node26": Taishan200Kunpeng9206426x2,
    "node52": Taishan200Kunpeng9204826x2,
    "rchehab": HuaweiMatebookXPro,
}
