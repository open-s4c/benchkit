# Copyright (C) 2023 Huawei Technologies Co., Ltd. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Plotbench is a web app allowing to parse a directory of CSV files and generate interactive
multi-line charts with the stored results.
"""

import os
import os.path
import sys
from typing import Any, Dict, List, Tuple

import dash
import pandas as pd
import plotly.express as px
from dash import dcc, html
from dash.dependencies import ALL, Input, Output, State
from plotly.graph_objects import Figure
from utils.dataframes import cross_sect, get_aggregates, get_dataset

from benchkit.utils.dir import parentdir
from benchkit.utils.types import PathType

PlotbenchFigure = Figure | Dict[str, Any]

if len(sys.argv) < 2:
    raise ValueError("Please provide search path on the command line.")

MAIN_DIR = sys.argv[1]
plotbench_src_path = parentdir(os.path.realpath(__file__))


def find_datadir(folder: PathType) -> str:
    """Find the data directories from the provided root directory."""
    for root, _, files in os.walk(folder):
        csv_files = [f for f in files if f.startswith("benchmark_") and f.endswith(".csv")]
        if csv_files:
            yield root


data_dirs = sorted(set(list(find_datadir(MAIN_DIR))))

external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap",
        "rel": "stylesheet",
    },
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.title = "Benchmark results"
app._favicon = "favicon.svg"  # pylint: disable=protected-access

with open(plotbench_src_path / "assets/defaultcustomsrc.txt", "r") as custom_src_file:
    custom_src_default = custom_src_file.read()


header = html.Div(
    children=[
        html.P(children="📉📊📈", className="header-emoji"),
        html.H1(children="Evaluation results", className="header-title"),
        html.P(
            children="Parsing datasets and plotting results",
            className="header-description",
        ),
    ],
    className="header",
)

menu1 = html.Div(
    children=[
        html.Div(
            children=[
                html.Div(children="Data directory", className="menu-title"),
                dcc.Dropdown(
                    id="datadir-filter",
                    options=[{"label": d.replace(MAIN_DIR, "", 1), "value": d} for d in data_dirs],
                    value=data_dirs[-1] if data_dirs else None,
                    clearable=False,
                    searchable=True,
                    className="dropdown",
                ),
            ],
            style={"width": "60%"},
        ),
    ],
    className="menu",
)

textout = html.Div(
    children=[
        html.P(
            id="textout",
            children="",
            hidden=True,
        )
    ],
    className="card",
)
warning_panel_coleng = html.Div(
    id="warning-pane-coleng",
    children=[
        html.Div(
            id="warning-text-coleng",
            children="WARNING: ...",
            className="warning",
        ),
    ],
    hidden=True,
    className="card",
)
LABEL_XTICKS_TEXT = "Label x-axis ticks"
PUT_IDEAL_LINE_TEXT = "Add ideal linear line"
iodefs = html.Div(
    id="iodefs",
    children=[
        html.Div(children="Columns engineering", className="menu-title"),
        warning_panel_coleng,
        dcc.Textarea(
            id="columns-eng-text",
            value=custom_src_default,
            style={"width": "100%", "height": 80},
        ),
        html.Button("Update", id="columns-eng-button", n_clicks=0),
        html.Div(children="x-axis", className="menu-title"),
        dcc.Dropdown(options=[], value=None, id="idefs-list", clearable=False, searchable=True),
        dcc.Checklist([LABEL_XTICKS_TEXT], [LABEL_XTICKS_TEXT], id="xtick-label-list"),
        html.Div(children="Color axis", className="menu-title"),
        dcc.Dropdown(options=[], value=None, id="colordefs-list", clearable=False, searchable=True),
        dcc.Checklist([PUT_IDEAL_LINE_TEXT], [], id="put-ideal-linear-list"),
        html.Div(children="Columns", className="menu-title"),
        dcc.Dropdown(options=[], value=None, id="coldefs-list", clearable=True, searchable=True),
        html.Div(children="Inputs", className="menu-title"),
        dcc.Checklist([], [], id="iodefs-list"),
    ],
    hidden=True,
    className="card",
)
YTICKS_ZERO_TEXT = "Starts y-axis at 0"
output_select = html.Div(
    id="outputsel",
    children=[
        html.Div(children="Select output (y-axis)", className="menu-title"),
        dcc.Dropdown(
            options=[],
            value=None,
            id="outputsel-dropdown",
            clearable=False,
            searchable=True,
        ),
        dcc.Checklist(
            [YTICKS_ZERO_TEXT],
            [YTICKS_ZERO_TEXT],
            id="yticks-zero-list",
        ),
    ],
    hidden=True,
    className="card",
)
filters_select = html.Div(
    id="filtersel",
    children=[
        html.Div(children="Select filters", className="menu-title"),
        dcc.Checklist([], [], id="filtersel-list"),
    ],
    hidden=True,
    className="card",
)
constants_panel = html.Div(
    id="constants-pane",
    children=[
        html.Div(children="Constants", className="menu-title"),
        html.Details(
            [
                html.Summary("Expand to see constant values."),
                dash.dash_table.DataTable(
                    id="constants",
                    data=None,
                    style_as_list_view=True,
                    style_header={"display": "none"},
                ),
            ]
        ),
    ],
    hidden=True,
    className="card",
)

warning_panel = html.Div(
    id="warning-pane",
    children=[
        html.Div(
            id="warning-text",
            children="WARNING: ...",
            className="warning",
        ),
    ],
    hidden=True,
    className="card",
)

graph = html.Div(
    children=[
        textout,
        iodefs,
        output_select,
        filters_select,
        html.Div(
            id="filters_select_dyn",
            className="card",
            hidden=True,
        ),
        constants_panel,
        warning_panel,
        html.Div(
            children=dcc.Graph(
                id="chart",
            ),
            className="card",
        ),
        html.Div(
            children=dcc.Graph(
                id="chart_dots",
            ),
            className="card",
        ),
    ],
    className="wrapper",
)

app.layout = html.Div(
    children=[
        header,
        menu1,
        graph,
        dcc.Store(id="stored-dataset"),
        dcc.Store(id="selected-traces"),
    ]
)


def to_json(df: pd.DataFrame) -> str:
    """Convert give dataframe to json string."""
    return df.to_json(date_format="iso", orient="split")


def from_json(json: str) -> pd.DataFrame:
    """Convert given json string to pandas dataframe."""
    return pd.read_json(json, orient="split")


def get_default_value(
    preferred_values: List[str],
    all_columns: List[str],
) -> str | None:
    """Get default value of a column given some preferred values."""
    for value in preferred_values:
        if value in all_columns:
            return value
    return all_columns[0] if len(all_columns) > 0 else None


@app.callback(
    [
        Output("textout", "children"),
        Output("textout", "hidden"),
        Output("idefs-list", "options"),
        Output("idefs-list", "value"),
        Output("colordefs-list", "options"),
        Output("colordefs-list", "value"),
        Output("coldefs-list", "options"),
        Output("coldefs-list", "value"),
        Output("iodefs-list", "options"),
        Output("iodefs-list", "value"),
        Output("iodefs", "hidden"),
        Output("stored-dataset", "data"),
        Output("warning-pane-coleng", "hidden"),
        Output("warning-text-coleng", "children"),
    ],
    [
        Input("datadir-filter", "value"),
        Input("columns-eng-button", "n_clicks"),
    ],
    State("columns-eng-text", "value"),
)
def update_data_dir(
    dd: PathType,
    _: int,  # ignore nb_clicks
    columns_eng_text: str,
) -> Tuple[
    List[str],
    bool,
    List[str],
    str,
    List[str],
    str,
    List[str],
    str,
    List[str],
    List[str],
    bool,
    str,
    bool,
    str,
]:
    """The selected data directory has been updated: trigger the generation of all submenus."""
    out_text = f"Obtained dd: {dd}"
    hidden = dd is None
    all_columns = []
    input_columns = []
    json_df = ""
    idef_val = None
    colordef_val = None
    coldef_val = None
    warning_coleng_hidden = True
    warning_coleng_text = ""

    if dd is not None:
        results_path = dd
        df = get_dataset(results_path)

        if columns_eng_text:  # custom columns
            try:
                exec(columns_eng_text)
            except KeyError:
                warning_coleng_hidden = False
                warning_coleng_text = "The code is not loaded, a KeyError has been detected"

        all_columns = list(df.columns)
        rep_index = all_columns.index("rep") + 1
        input_columns = all_columns[:rep_index]
        json_df = to_json(df)

        def non_all_thread(column: str) -> bool:
            if not column.startswith("thread_"):
                return True
            thread_nb_str = column.strip().split("_")[-1].strip()
            if not thread_nb_str.isdigit():
                return True
            thread_nb = int(thread_nb_str)
            if thread_nb < 5:
                return True
            return False

        all_columns = [
            c for c in all_columns if non_all_thread(c)
        ]  # filter out all thread_1+ to avoid bloating

        idef_val = get_default_value(
            preferred_values=["nb_threads", "nb_cores"],
            all_columns=all_columns,
        )
        colordef_val = get_default_value(
            preferred_values=["lock", "lock_pretty"],
            all_columns=all_columns,
        )
        coldef_val = get_default_value(
            preferred_values=["Platform", "architecture"],
            all_columns=all_columns,
        )

    return (
        [out_text],
        hidden,
        all_columns,
        idef_val,
        all_columns,
        colordef_val,
        all_columns,
        coldef_val,
        all_columns,
        input_columns,
        hidden,
        json_df,
        warning_coleng_hidden,
        warning_coleng_text,
    )


@app.callback(
    [
        Output("outputsel", "hidden"),
        Output("outputsel-dropdown", "options"),
        Output("outputsel-dropdown", "value"),
        Output("filtersel", "hidden"),
        Output("filtersel-list", "options"),
        Output("constants", "data"),
        Output("constants-pane", "hidden"),
    ],
    [
        Input("iodefs-list", "options"),
        Input("iodefs-list", "value"),
        Input("stored-dataset", "data"),
    ],
)
def output_select_f(
    all_columns: List[str],
    input_columns: List[str],
    json_df: str,
) -> Tuple[bool, List[str], str, bool, List[str], List[Dict[str, str]], bool]:
    """Prepare selection of outputs."""
    if not all_columns:
        return True, [], "", True, [], [], True

    dataset = from_json(json_df) if json_df else None

    def is_variable(column):
        if dataset is None:
            return True
        return len(dataset[column].unique()) > 1

    output_columns = [c for c in all_columns if c not in input_columns]
    sorted_input_columns = [c for c in all_columns if c in input_columns]
    variable_input_columns = [c for c in sorted_input_columns if is_variable(c)]
    constant_input_columns = [c for c in sorted_input_columns if c not in variable_input_columns]

    default = get_default_value(
        preferred_values=["throughput", "tps"],
        all_columns=output_columns,
    )

    constants_dict = {c: dataset[c].unique()[0] for c in constant_input_columns}
    constants_panel_dict = [{"name": k, "value": v} for k, v in constants_dict.items()]

    return (
        False,
        output_columns,
        default,
        False,
        variable_input_columns,
        constants_panel_dict,
        False,
    )


@app.callback(
    [
        Output("filters_select_dyn", "hidden"),
        Output("filters_select_dyn", "children"),
    ],
    [
        Input("stored-dataset", "data"),
        Input("filtersel-list", "value"),
    ],
)
def filters_select_f(
    json_df: str,
    selected_filters: List[str],
) -> Tuple[bool, List[Any]]:
    """Prepare selection of filters."""
    dataset = from_json(json_df) if json_df else None
    if dataset is None:
        return True, []

    def get_dropdown(key):
        options = sorted(dataset[key].unique())
        return html.Div(
            children=[
                html.Div(children=f"{key}:", className="menu-title"),
                dcc.Dropdown(
                    id={"type": "filter-dropdown", "index": key},
                    options=options,
                    value=options[0],
                    clearable=False,
                    searchable=True,
                    className="dropdown",
                ),
            ],
        )

    dropdowns = [get_dropdown(k) for k in selected_filters]

    return False, dropdowns


@app.callback(
    [
        Output("chart", "figure"),
        Output("chart_dots", "figure"),
        Output("warning-pane", "hidden"),
        Output("warning-text", "children"),
    ],
    [
        Input("stored-dataset", "data"),
        State("selected-traces", "data"),
        Input("iodefs-list", "value"),
        Input("outputsel-dropdown", "value"),
        Input({"type": "filter-dropdown", "index": ALL}, "id"),
        Input({"type": "filter-dropdown", "index": ALL}, "value"),
        Input("idefs-list", "value"),
        Input("colordefs-list", "value"),
        Input("coldefs-list", "value"),
        Input("xtick-label-list", "value"),
        Input("put-ideal-linear-list", "value"),
        Input("yticks-zero-list", "value"),
    ],
)
def update_charts(  # TODO check input_columns argument
    json_df: str,
    selected_traces: List[str] | None,
    input_columns: List[str],  # pylint: disable=unused-argument
    output_key: str,
    filters_dd_names: List[Dict[str, str]],
    filters_dd_values: List[str],
    x_ax_name: str,
    color_ax_name: str,
    col_ax_name: str,
    xtick_label_list: List[str],
    put_ideal_linear_list: List[str],
    yticks_zero_list,
) -> Tuple[PlotbenchFigure, PlotbenchFigure, bool, str]:
    """Update the charts according to menu selection."""
    dataset = from_json(json_df) if json_df else None
    label_xticks = LABEL_XTICKS_TEXT in xtick_label_list
    put_ideal_linear = PUT_IDEAL_LINE_TEXT in put_ideal_linear_list
    yticks_zero = YTICKS_ZERO_TEXT in yticks_zero_list
    aggreg_warning_text = ""
    aggreg_warning_hidden = True

    if dataset is not None:
        x_ax = x_ax_name
        y_ax = output_key
        z_ax = color_ax_name
        col_ax = col_ax_name

        xticks = sorted(dataset[x_ax].unique())

        xs = dict(zip([e["index"] for e in filters_dd_names], filters_dd_values))
        xdf = cross_sect(
            df=dataset,
            cross_section_dict=xs,
            drop_level=False,
        ).reset_index()

        sort_keys = list({k for k in [col_ax, z_ax, x_ax] if k is not None})
        xdf.sort_values(by=sort_keys + ["rep"], inplace=True)

        aggr_ind = get_aggregates(
            dataset=dataset,
            cross_section_dict=xs,
            color_axis=z_ax,
            x_axis=x_ax,
            y_axis=y_ax,
            column_axis=col_ax,
            put_ideal_linear=put_ideal_linear,
        )
        aggr = aggr_ind.reset_index()
        aggr.sort_values(by=sort_keys, inplace=True)

        unique_counts = aggr["count"].unique()
        max_count = dataset["rep"].max()
        max_granularity_aggreg = len(unique_counts) == 1 and unique_counts[0] == max_count
        if not max_granularity_aggreg:
            aggreg_warning_text = (
                "WARNING: the aggregation currently aggregates "
                "over several dimensions, not only the repetitions. "
                "Please enable filters or column/color axes."
            )
            aggreg_warning_hidden = False

        def update_fig(fig):
            fig.update_traces(marker={"size": 8})
            if label_xticks:
                fig.update_xaxes(tickvals=xticks)
            if yticks_zero:
                fig.update_yaxes(rangemode="tozero")

        fig_lines = px.line(
            aggr,
            x=x_ax,
            y=f"{y_ax} mean",
            color=z_ax,
            symbol=z_ax,
            markers=True,
            facet_col=col_ax,
        )
        update_fig(fig_lines)

        if selected_traces is None:
            selected_traces = {}
        for fig_trace in fig_lines.select_traces():
            if fig_trace.name not in selected_traces:
                selected_traces[fig_trace.name] = True
            if not selected_traces[fig_trace.name]:
                fig_trace.visible = "legendonly"

        fig_dots = px.scatter(
            xdf,
            x=x_ax,
            y=y_ax,
            color=z_ax,
            symbol=z_ax,
            facet_col=col_ax,
        )
        update_fig(fig_dots)

        return fig_lines, fig_dots, aggreg_warning_hidden, aggreg_warning_text

    dfig = {
        "data": [
            {
                "x": [],
                "y": [],
                "color": [],
                "type": "lines",
            },
        ],
        "layout": {
            "title": {"text": f"Mean {output_key}", "x": 0.05, "xanchor": "left"},
            "xaxis": {"fixedrange": True},
            "yaxis": {"fixedrange": True},
            "colorway": ["#E12D39"],
        },
    }
    return dfig, dfig, aggreg_warning_hidden, aggreg_warning_text


@app.callback(
    Output("selected-traces", "data"),
    [
        Input("chart", "restyleData"),
        State("selected-traces", "data"),
        State("chart", "figure"),
        State("chart_dots", "figure"),
    ],
)
def legend_click(  # TODO check fig_dots argument
    restyle_data,
    selected_traces,
    fig_lines,
    fig_dots,  # pylint: disable=unused-argument
):
    """The legend is clicked and only some colors are selected."""
    if restyle_data is None:
        return selected_traces

    attr_list, indexes = restyle_data
    if "visible" in attr_list:
        for attr, i in zip(attr_list["visible"], indexes):
            trace_name = fig_lines["data"][i]["name"]

            if selected_traces is None:
                selected_traces = {}
            if isinstance(attr, str) and "legendonly" == attr:
                selected_traces[trace_name] = False
            elif isinstance(attr, bool) and attr:
                selected_traces[trace_name] = True
            else:
                raise ValueError("Unsupported type for restyleData attribute.")

    return selected_traces


if __name__ == "__main__":
    app.run_server("0.0.0.0", debug=True)
