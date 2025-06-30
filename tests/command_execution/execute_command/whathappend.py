import datetime
from math import inf
import time
from bokeh.plotting import figure, show
import csv

import numpy as np

from bokeh.layouts import column
from bokeh.models import ColumnDataSource, RangeTool
from bokeh.plotting import figure, show
from bokeh.models import HoverTool

demodict = {
    "start_time":0,
    "duration":8,
    "command_name":"wafel",
    "events":[(14,"wafel_output")]
}


import glob
print(glob.glob("./.commandlogging/*"))
l = sorted(glob.glob("./.commandlogging/*"))
latest = l[-1]
objects = []
for x in glob.glob(latest+'/*'):
    with open(x) as f:
        header = f.readline()
        header_values = f.readline()
        obj = next(csv.DictReader([header,header_values]))
        events = []
        data_line = f.readline().strip()
        while data_line != "hookend" and data_line:
            field = data_line.split(',')
            events.append(field)
            data_line = f.readline().strip()
        obj["events"] = events
        dur = f.readline()
        if dur:
            obj["duration"] = float(dur.strip()) * 1000
        else:
            obj["duration"] = float(200000) * 1000

        objects.append(obj)

minimum = inf
maximum = -inf
for x in objects:
    if float(x["hookstart"]) < minimum:
        minimum = float(x["hookstart"])

for x in objects:
    new_events = []
    for event in x["events"]:
        new_events.append((datetime.datetime.fromtimestamp(float(event[0])),event[1],event[2]))
    x["events"] = new_events
    x["hookstart"] = datetime.datetime.fromtimestamp(float(x["hookstart"]))
objects = sorted(objects,key=lambda x: x["hookstart"])

_tools_to_show = 'box_zoom,pan,save,hover,resize,reset,tap,wheel_zoom'

p = figure(height=300, width=800, tools="xpan,xwheel_zoom,reset",
           x_axis_type="datetime", x_axis_location="above", window_axis="x",
           background_fill_color="#efefef",)

select = figure(title="Drag the middle and edges of the selection box to change the range above",
                height=130, width=800,
                x_axis_type="datetime", y_axis_type=None,
                tools="", toolbar_location=None, background_fill_color="#efefef")
select.x_range.range_padding = 0
select.x_range.bounds = "auto"

range_tool = RangeTool(x_range=p.x_range, start_gesture="pan")
range_tool.overlay.fill_color = "navy"
range_tool.overlay.fill_alpha = 0.2


for idx, obj in enumerate(objects):
    s = ColumnDataSource(
        data= dict(
            x=[obj["hookstart"]],
            y=[idx],
            location=[obj["location"]],
            a=["1"]
        )
    )
    print([float(obj["duration"])])
    bl = p.block(source=s, width=float(obj["duration"]), height=1,fill_alpha=0.5)


    select.block(x=obj["hookstart"], y=idx, width=float(obj["duration"]), height=1,
                 fill_alpha=0.5,
                 )
    TOOLTIPS = [
                ("location", "@location"),
                ("a","@a")
            ]
    bl_hover = HoverTool(renderers=[bl],
                         tooltips=TOOLTIPS)
    p.add_tools(bl_hover)
    events = []
    if obj["events"]:
        for a in obj["events"]:
            source = ColumnDataSource(data=dict(
                x=[a[0]],
                y=[idx+0.5],
                desc=[a[1] + a[2]],
            ))
            gr = p.scatter(source=source,
            size=10, color="red", alpha=0.5)
            TOOLTIPS = [
                ("data", "@desc"),
            ]

            g1_hover = HoverTool(renderers=[gr],
                         tooltips=TOOLTIPS)
            p.add_tools(g1_hover)


            events.append(a[0])
        select.scatter(events, idx+0.5,
            size=4, color="olive", alpha=0.5)


select.ygrid.grid_line_color = None
select.add_tools(range_tool)


show(column(p, select))