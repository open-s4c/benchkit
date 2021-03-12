# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities to create printed charts with Matplotlib.
"""

import os.path as ospath
from datetime import datetime


def export_figure(
    plot,
    path,
    creation_year,
    creation_month,
    creation_day,
):
    """Export figure as a pdf and fix the date (for reproducible figure generation)."""
    output_path = ospath.realpath(path)
    ext = ospath.splitext(output_path)[-1]

    the_date = datetime(creation_year, creation_month, creation_day, 12, 0)

    output_fig = plot
    if hasattr(plot, "figure"):
        if plot.figure is not None:
            output_fig = plot.figure

    metadata = None
    if ".pdf" == ext:
        metadata = {
            "CreationDate": the_date,
            "ModDate": the_date,
        }

    output_fig.savefig(
        output_path,
        metadata=metadata,
        pad_inches=0.1,
        bbox_inches="tight",
    )
