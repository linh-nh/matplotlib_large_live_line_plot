import time
import math
from bisect import bisect_left
import random
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import matplotlib as mpl
from matplotlib.backend_bases import MouseButton

import threading

import pathlib
import tkinter as tk
import tkinter.ttk as ttk
import pygubu

##### PARAMETER #############

#number of data channel
NUM_CHANNEL = 2
#fixed number of data point in plot view, also number of data point to subsample
#cannot view more or less than this number
MAX_NUM_POINT_IN_VIEW = 1000
#to calculate next zoom level, the difference with the old zoom level
#must be more than this number of data point
MIN_ZOOM = 200
MAX_ZOOM_LEVEL = 100
#mouse button for pan action, recommneded to be right mouse button
#because left mouse is used by built-in zoom-in
PAN_BUTTON = 3

########## END PARAMETER###########

time_data = []
channel_data = []
for i in range (NUM_CHANNEL):
    channel_data.append(list())
    channel_data.append(list())

#there is a delay when updating channels' data, so use this func to get len
def get_data_len():
    min_len = len(time_data)
    for i in range(0,NUM_CHANNEL):
        check = len(channel_data[i])
        if check < min_len:
            min_len = check
    return min_len

# a separate thread to update data, simulated
def data_thread():
    global time_data
    global channel_data
    first_data_time = time.time()
    print_time = 10
    while True:
        t = time.time() - first_data_time
        time_data.append(t)
        channel_data[0].append(math.sin(t*0.5) + random.random()*0.5)
        channel_data[1].append(2*(math.cos(t*0.5) + random.random()*0.5))
        if t > print_time:
            print_time = print_time+10
        time.sleep(0.001)
            
                
t1 = threading.Thread(target=data_thread)
t1.start()

class gui_cb:
    def slide_changed(val):
        global live
        global cur_view_len
        global cur_start
        global cur_zoom_level
        global slider
        data_len = get_data_len()
        if live:
            cur_start = data_len - cur_view_len
        if data_len <= MAX_NUM_POINT_IN_VIEW:
            builder.tkvariables['slider_val'].set(MAX_ZOOM_LEVEL - cur_zoom_level)
            return
        next_zoom_level = MAX_ZOOM_LEVEL - int(val)
        next_view_len = MAX_NUM_POINT_IN_VIEW + (data_len - MAX_NUM_POINT_IN_VIEW) / MAX_ZOOM_LEVEL * next_zoom_level
        if not live:
            next_start = cur_start + cur_view_len / 2 - next_view_len / 2
            if next_start < 0:
                next_start = 0
            if next_start + next_view_len >= data_len:
                live = True
            cur_start = int(next_start)

        cur_view_len = int(next_view_len)
        
        cur_zoom_level = next_zoom_level
        builder.tkvariables['slider_val'].set(MAX_ZOOM_LEVEL - cur_zoom_level)
        draw()
        
PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI = PROJECT_PATH / "matplotlib_large_live.ui"
builder = pygubu.Builder()
builder.add_resource_path(PROJECT_PATH)
builder.add_from_file(PROJECT_UI)
mainwindow = builder.get_object('toplevel1', None)
fcontainer = builder.get_object('fcontainer')
fig = Figure()
canvas = FigureCanvasTkAgg(fig, master=fcontainer)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
toolbar = NavigationToolbar2Tk(canvas, fcontainer)
toolbar.update()
canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
builder.connect_callbacks(gui_cb)
slider = builder.get_object('zoom')
slider.configure(from_ = 0, to = MAX_ZOOM_LEVEL, resolution = 1)



ax1 = fig.add_subplot(111)
ax2 = ax1.twinx()
ax1.set_xlabel('time(s)')
ax1.set_ylabel('channel 0')
ax2.set_ylabel('channel 1')

ax1.tick_params(axis = 'x', which = 'both', top = False)
ax1.tick_params(axis = 'y', which = 'both', right = False, colors = 'red')
ax2.tick_params(axis = 'y', which = 'both', right = True, labelright = True, left = False, labelleft = False, colors = 'blue')

cur_start = 0
cur_zoom_level = MAX_ZOOM_LEVEL
cur_view_len = 0

live = True
slider.set(MAX_ZOOM_LEVEL - cur_zoom_level)

def mouse_move_cb(event):
    global live
    global cur_start
    global drag_start
    if event.inaxes is not None and event.button == PAN_BUTTON:
        if cur_zoom_level == MAX_ZOOM_LEVEL:
            return
        data_len = get_data_len()
        if live:
            cur_start = data_len - cur_view_len
        drag_to = bisect_left(time_data, event.xdata)
        cur_start = cur_start - drag_to + drag_start
        if cur_start + cur_view_len >= data_len:
            live = True
            cur_start = data_len - cur_view_len
        else:
            live = False
        if cur_start < 0:
            cur_start = 0
        draw()
        

def mouse_button_cb(event):
    global drag_start
    if event.inaxes is not None and event.button == PAN_BUTTON:
        if cur_zoom_level == MAX_ZOOM_LEVEL:
            return
        drag_start = bisect_left(time_data, event.xdata)
        
def mouse_scroll_cb(event):
    global live
    global cur_view_len
    global cur_start
    global cur_zoom_level
    global slider
    if event.inaxes is not None:

        data_len = get_data_len()
        if cur_zoom_level == 0 and event.step > 0: #already min zoom
            return
        if cur_zoom_level == MAX_ZOOM_LEVEL:
            if event.step < 0: # already max zoom
                return
            cur_view_len = data_len
        if live:
            cur_start = data_len - cur_view_len
        if data_len <= MAX_NUM_POINT_IN_VIEW:
            return

        if event.step < 0: # zoom out
            next_zoom_level = math.ceil((MIN_ZOOM + cur_view_len - MAX_NUM_POINT_IN_VIEW) / ((data_len - MAX_NUM_POINT_IN_VIEW) / MAX_ZOOM_LEVEL))
        else: # zoom in
            next_zoom_level = math.floor((cur_view_len - MIN_ZOOM - MAX_NUM_POINT_IN_VIEW) / ((data_len - MAX_NUM_POINT_IN_VIEW) / MAX_ZOOM_LEVEL))

        if cur_zoom_level == next_zoom_level:
            next_zoom_level = next_zoom_level - event.step

        if next_zoom_level > MAX_ZOOM_LEVEL:
            next_zoom_level = MAX_ZOOM_LEVEL
        elif next_zoom_level < 0:
            next_zoom_level = 0;
        next_view_len = MAX_NUM_POINT_IN_VIEW + (data_len - MAX_NUM_POINT_IN_VIEW) / MAX_ZOOM_LEVEL * next_zoom_level
        xind = bisect_left(time_data, event.xdata)
        next_start = xind - (xind - cur_start)/ cur_view_len * next_view_len
        if next_start < 0:
            next_start = 0
        if next_start + next_view_len >= data_len:
            live = True
        else:
            live = False
        cur_view_len = int(next_view_len)
        cur_start = int(next_start)
        cur_zoom_level = next_zoom_level
        builder.tkvariables['slider_val'].set((MAX_ZOOM_LEVEL - cur_zoom_level))
        #print(str(cur_zoom_level) + " " + str(cur_start) + " " + str(cur_view_len) + " " + str(data_len) + " " + str(live))

        draw()

fig.canvas.callbacks.connect('scroll_event', mouse_scroll_cb)
fig.canvas.callbacks.connect('button_press_event', mouse_button_cb)
fig.canvas.callbacks.connect('motion_notify_event', mouse_move_cb)

def subsample(data):
    ratio = len(data[0]) / MAX_NUM_POINT_IN_VIEW
    sub = []
    for i in range(0, len(data)):
        sub.append(list())
    for i in range(0, MAX_NUM_POINT_IN_VIEW):
        for j in range(0, len(data)):
            sub[j].append(data[j][int(i*ratio)])
    return sub

#update each 500ms
def periodic():
    draw()
    mainwindow.after(500, periodic)

prev_view_len = 0
prev_start = 0
def draw():
    global prev_view_len
    global prev_start
    if not live:
        if prev_view_len == cur_view_len and prev_start == cur_start:
            return
        else:
            prev_view_len = cur_view_len
            prev_start = cur_start

    min_len = get_data_len()
    if cur_zoom_level == MAX_ZOOM_LEVEL:
        data_to_sub = [time_data[:min_len]]
        for i in range(0, NUM_CHANNEL):
            data_to_sub.append(channel_data[i][:min_len])
        if min_len <= MAX_NUM_POINT_IN_VIEW:
            sub = data_to_sub
        else:
            sub = subsample(data_to_sub)
    else:
        if live:
            data_to_sub = [time_data[min_len-cur_view_len:min_len]]
            for i in range(0, NUM_CHANNEL):
                data_to_sub.append(channel_data[i][min_len-cur_view_len:min_len])
        else:
            data_to_sub = [time_data[cur_start:cur_start+cur_view_len]]
            for i in range(0, NUM_CHANNEL):
                data_to_sub.append(channel_data[i][cur_start:cur_start+cur_view_len])
        if cur_view_len <= MAX_NUM_POINT_IN_VIEW:
            sub = data_to_sub
        else:
            sub = subsample(data_to_sub)

    #draw plot
    ax1.cla()
    ax2.cla()
    #sub[0] is time, sub[1] is channel 1 ...
    line1 = ax1.plot(sub[0], sub[1], color = 'red')
    line2 = ax2.plot(sub[0], sub[2], color = 'blue')

    plt.xlim(sub[0][0], sub[0][-1])
    maxy0 = max(sub[1])
    miny0 = min(sub[1])
    maxy1 = max(sub[2])
    miny1 = min(sub[2])
    ax1.set_ylim(miny0, maxy0)
    ax2.set_ylim(miny1, maxy1)
    fig.tight_layout()
    canvas.draw()


draw()
#update each 500ms
mainwindow.after(500, periodic)
mainwindow.mainloop()


