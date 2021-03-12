# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Utilities to create interactive charts with Altair.
Due to plotbench, we might deprecate that soon.
"""

import altair as alt


def create_selector(
    name,
    key,
    values,
    init=None,
    radio=False,
):
    """Create a selector for the altair interactive graph (dropdown)."""
    binder_fun = alt.binding_radio if radio else alt.binding_select
    binder = binder_fun(options=values)
    selector = alt.selection_single(
        name=name,
        fields=[key],
        bind=binder,
        init={key: values[0] if init is None else init},
    )
    return selector


def apply_selector(chart, selector):
    """Attach the given selector to the given Altair chart."""
    return chart.add_selection(selector).transform_filter(selector)


def field_selector(name, df):
    """
    Create a selector for a single field, taking a column from the given dataframe and filter
    according to each possible value in that column.
    """
    return create_selector(
        name,
        name,
        sorted(set(df[name])),
    )


def apply_selectors(chart, selectors):
    """Attach a list of selectors to the given graph."""
    current_chart = chart
    for sel in selectors:
        current_chart = apply_selector(current_chart, sel)
    return current_chart
