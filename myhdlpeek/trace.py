# -*- coding: utf-8 -*-

# Copyright (c) 2017-2020, XESS Corp. The MIT License (MIT).

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import math
import operator
from builtins import dict, int, str, super
from collections import namedtuple
from copy import copy

import IPython.display as DISP
import matplotlib.pyplot as plt
import pandas as pd
from future import standard_library
from tabulate import tabulate

standard_library.install_aliases()


# Waveform samples consist of a time and a value.
Sample = namedtuple("Sample", "time value")


class Trace(list):
    """
    Trace objects are lists that store a sequence of samples. The samples
    should be arranged in order of ascending sample time.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = None
        self.num_bits = 0

    def store_sample(self, value, time):
        """Store a value and the current time into the trace."""
        self.append(Sample(time, copy(value)))

    def insert_sample(self, sample):
        """Insert a sample into the correct position within a trace"""
        index = self.get_index(sample.time)
        self.insert(index, sample)

    def start_time(self):
        """Return the time of the first sample in the trace."""
        return self[0].time

    def stop_time(self):
        """Return the time of the last sample in the trace."""
        return self[-1].time

    def get_index(self, time):
        """Return the position to insert a sample with the given time."""

        for i, sample in enumerate(self):
            # Return the index of the 1st sample with a time GREATER than the
            # given time because the sample will be inserted BEFORE that index.
            if sample.time > time:
                return i

        # Didn't find a sample with a time greater than the given time, so
        # the insertion point is the end of the trace list.
        return len(self)

    def get_value(self, time):
        """Get the trace value at an arbitrary time."""

        # Return the signal value immediately BEFORE the insertion index.
        return self[max(0, self.get_index(time) - 1)].value

    def get_sample_times(self, **kwargs):
        """Return list of times at which the trace was sampled."""
        start_time = kwargs.pop("start_time", self.start_time())
        stop_time = kwargs.pop("stop_time", self.stop_time())
        return [
            sample.time for sample in self if start_time <= sample.time <= stop_time
        ]

    def delay(self, delta):
        """Return the trace data shifted in time by delta units."""
        delayed_trace = Trace([Sample(t + delta, v) for t, v in self])
        delayed_trace.name = self.name
        delayed_trace.num_bits = self.num_bits
        return delayed_trace

    def extend_duration(self, start_time, end_time):
        """Extend the duration of a trace."""
        # Extend the trace data to start_time unless the trace data already precedes that.
        if start_time < self[0].time:
            self.insert(0, Sample(start_time, self[0].value))
        # Extend the trace data to end_time unless the trace data already exceeds that.
        if end_time > self[-1].time:
            self.append(Sample(end_time, self[-1].value))

    def remove_repeats(self):
        """Return a trace without samples having the same sampling time."""
        trace = copy(self)
        trace.clear()

        # Build the trace backwards, starting from the oldest sample.
        # Skip any sample having a time >= the most recently accepted sample.
        trace.append(self[-1])
        for sample in self[-1::-1]:
            if sample.time < trace[0].time:
                trace.insert(0, sample)

        return trace

    def interpolate(self, times):
        """Insert interpolated values at the times in the given list."""
        for time in times:
            insert_sample(Sample(self.get_value(time), time))

    def add_rise_fall(self, delta):
        """Add rise/fall time to trace transitions."""
        trace = self.remove_repeats()
        prev_sample = trace[0]
        for sample in trace[1:]:
            trace.insert_sample(Sample(sample.time - delta, prev_sample.value))
            prev_sample = sample
        return trace

    def add_slope(self):
        """Return a trace with slope added to trace transitions."""
        return self.add_rise_fall(0.2).delay(0.1)

    def binarize(self):
        """Return trace of sample values set to 1 (if true) or 0 (if false)."""
        return Trace([Sample(t, (v and 1) or 0) for t, v in self])

    def toggles(self):
        """Return a binary trace that toggles wherever the source trace changes values."""
        toggle_trace = copy(self)
        toggle_trace.clear()
        toggle_trace.append(Sample(self[0].time, 1))  # Define starting point.
        for sample in self.anyedge():
            if sample.value:
                tgl_val = toggle_trace[-1].value
                tgl_val = (not tgl_val and 1) or 0
                toggle_trace.append(Sample(sample.time, tgl_val))
        # Define ending point.
        toggle_trace.append(Sample(self[-1].time, toggle_trace[-1].value))
        toggle_trace.num_bits = 1
        return toggle_trace

    def apply_op1(self, op_func):
        """Return trace generated by applying the operator function to all the sample values in the trace."""
        return Trace([Sample(t, op_func(v)) for t, v in self])

    def apply_op2(self, trc, op_func):
        """Return trace generated by applying the operator function to two traces."""

        if isinstance(trc, Trace):
            pass

        # If the function input is a constant, then make a trace from it.
        elif isinstance(trc, (int, float)):
            trc = Trace([Sample(0, trc)])

        # See if the input object contains a trace.
        else:
            try:
                trc = trc.trace
            except AttributeError:
                pass

        # Abort if operating on something that's not a Trace.
        if not isinstance(trc, Trace):
            raise Exception(
                "Trace can only be combined with another Trace or a number."
            )

        # Make copies of the traces since they will be altered.
        trc1 = copy(self)
        trc2 = copy(trc)

        # Extend the traces so they start/end at the same time.
        start_time = min(trc1[0].time, trc2[0].time)
        end_time = max(trc1[-1].time, trc2[-1].time)
        trc1.extend_duration(start_time, end_time)
        trc2.extend_duration(start_time, end_time)

        # Make a trace to hold the result generated by combining the two traces.
        res_trc = Trace([])

        # Loop through the trace samples, always using the earliest sample of the two.
        indx1 = 0  # Index of current sample in trc1.
        indx2 = 0  # Index of current sample in trc2.
        while True:
            # Find the earliest sample of the two traces and get the value
            # of each trace at that time.
            t1, v1 = trc1[indx1]
            t2, v2 = trc2[indx2]
            if t1 <= t2:
                curr_time = t1
            else:
                curr_time = t2
            v2 = trc2.get_value(curr_time)
            v1 = trc1.get_value(curr_time)

            # Combine the trace values using the operator.
            res_trc_val = op_func(v1, v2)

            # Append result to the results trace.
            res_trc.append(Sample(curr_time, res_trc_val))

            # Looped through all samples if each index is pointing to the
            # last sample in their traces.
            if indx1 == len(trc1) - 1 and indx2 == len(trc2) - 1:
                break

            # Move to next sample after the current time. (Might need to
            # increment both traces if they both had samples at the current time.)
            if t1 == curr_time:
                indx1 += 1
            if t2 == curr_time:
                indx2 += 1

        # Return trace containing the result of the operation.
        return res_trc

    def __eq__(self, trc):
        return self.apply_op2(trc, operator.eq).binarize()

    def __ne__(self, trc):
        return self.apply_op2(trc, operator.ne).binarize()

    def __le__(self, trc):
        return self.apply_op2(trc, operator.le).binarize()

    def __ge__(self, trc):
        return self.apply_op2(trc, operator.ge).binarize()

    def __lt__(self, trc):
        return self.apply_op2(trc, operator.lt).binarize()

    def __gt__(self, trc):
        return self.apply_op2(trc, operator.gt).binarize()

    def __add__(self, trc):
        return self.apply_op2(trc, operator.add)

    def __sub__(self, trc):
        return self.apply_op2(trc, operator.sub)

    def __mul__(self, trc):
        return self.apply_op2(trc, operator.mul)

    def __floordiv__(self, trc):
        return self.apply_op2(trc, operator.floordiv)

    def __truediv__(self, trc):
        return self.apply_op2(trc, operator.truediv)

    def __mod__(self, trc):
        return self.apply_op2(trc, operator.mod)

    def __lshift__(self, trc):
        return self.apply_op2(trc, operator.lshift)

    def __rshift__(self, trc):
        return self.apply_op2(trc, operator.rshift)

    def __and__(self, trc):
        return self.apply_op2(trc, operator.and_)

    def __or__(self, trc):
        return self.apply_op2(trc, operator.or_)

    def __xor__(self, trc):
        return self.apply_op2(trc, operator.xor)

    def __pow__(self, trc):
        return self.apply_op2(trc, operator.pow)

    def __pos__(self):
        return self.apply_op1(operator.pos)

    def __neg__(self):
        return self.apply_op1(operator.neg)

    def __not__(self):
        return self.apply_op1(operator.not_).binarize()

    def __inv__(self):
        return self.apply_op1(operator.inv)

    def __invert__(self):
        return self.apply_op1(operator.invert)

    def __abs__(self):
        return self.apply_op1(operator.abs)

    def anyedge(self):
        return (self != self.delay(1)).binarize()

    def posedge(self):
        return (self & (~self.delay(1))).binarize()

    def negedge(self):
        return ((~self) & self.delay(1)).binarize()

    def trig_times(self):
        """Return list of times trace value is true (non-zero)."""
        return [sample.time for sample in self if sample.value]

    def to_matplotlib(self, subplot, start_time, stop_time):
        """Fill a matplotlib subplot for a trace between the start & stop times."""

        # Set the X axis limits.
        subplot.set_xlim(start_time, stop_time + 0.005)

        # Set the Y axis limits.
        subplot.set_ylim(-0.2, 1.2)

        # Set the Y axis label position for each plot trace.
        ylbl_position = dict(
            rotation=0, horizontalalignment="right", verticalalignment="center", x=-0.01
        )
        subplot.set_ylabel(self.name, ylbl_position)

        # Remove ticks from Y axis.
        subplot.set_yticks([])
        subplot.tick_params(axis="y", length=0, which="both")

        # Remove the box around the subplot.
        subplot.spines["left"].set_visible(False)
        subplot.spines["right"].set_visible(False)
        subplot.spines["top"].set_visible(False)
        subplot.spines["bottom"].set_visible(False)

        # Insert samples for beginning/end times into a copy of the trace data.
        trace = copy(self)
        start = math.floor(start_time)
        stop = math.ceil(stop_time)
        trace.insert_sample(Sample(start, self.get_value(start)))
        trace.insert_sample(Sample(stop, self.get_value(stop)))

        # Remove samples having the same sample time, leaving only one.
        trace = trace.remove_repeats()

        # Plot the bus or binary trace.
        if trace.num_bits > 1:
            # Multi-bit bus trace.

            # Create a binary trace that toggles whenever the bus trace changes values.
            tgl_trace = trace.toggles()

            # Print bus values at midpoints of the bus packets.
            time0 = tgl_trace[0].time
            for tgl in tgl_trace[1:]:
                time1 = tgl.time
                if time0 < start_time:
                    time0 = start_time
                if time1 <= time0:
                    time0 = time1
                    continue
                if time1 > stop_time:
                    time1 = stop_time
                val = str(trace.get_value(time0))
                text_x = (time1 + time0) / 2
                text_y = 0.5
                subplot.text(
                    text_x,
                    text_y,
                    val,
                    horizontalalignment="center",
                    verticalalignment="center",
                )
                time0 = time1
                if time0 >= stop_time:
                    break

            # Slope the transitions of the trace waveform.
            tgl_trace = tgl_trace.add_slope()

            # Create a complementary trace for drawing bus packets.
            bar_trace = tgl_trace.__not__()

            # Generate the x,y data points for plotting the trace packets.
            x = [sample.time for sample in tgl_trace]
            x.append(trace[-1].time)
            y = [sample.value for sample in tgl_trace]
            y.append(y[-1])
            y_bar = [sample.value for sample in bar_trace]
            y_bar.append(y_bar[-1])
            subplot.plot(x, y, "tab:blue", x, y_bar, "tab:blue")

        else:
            # Binary trace.
            trace = trace.add_slope()
            x = [sample.time for sample in trace]
            x.append(trace[-1].time)
            y = [sample.value for sample in trace]
            y.append(y[-1])
            subplot.plot(x, y, "tab:blue")

    def to_wavejson(self, start_time, stop_time):
        """Generate the WaveJSON data for a trace between the start & stop times."""

        has_samples = False  # No samples currently on the wave.
        wave_str = ""  # No samples, so wave string is empty.
        wave_data = list()  # No samples, so wave data values are empty.
        prev_time = start_time  # Set time of previous sample to the wave starting time.
        prev_val = None  # Value of previous sample starts at non-number.

        # Save the current state of the waveform.
        prev = [has_samples, wave_str, copy(wave_data), prev_time, prev_val]

        # Insert samples into a copy of the waveform data. These samples bound
        # the beginning and ending times of the waveform.
        bounded_samples = copy(self)
        bounded_samples.insert_sample(Sample(start_time, self.get_value(start_time)))
        bounded_samples.insert_sample(Sample(stop_time, self.get_value(stop_time)))

        # Create the waveform by processing the waveform data.
        for time, val in bounded_samples:

            # Skip samples before the desired start of the time window.
            if time < start_time:
                continue

            # Exit the loop if the current sample occurred after the time window.
            if time > stop_time:
                break

            # If a sample occurred at the same time as the previous sample,
            # then revert back to the previous waveform to remove the previous
            # sample and put this new sample in its place.
            if time == prev_time:
                has_samples, wave_str, wave_data, prev_time, prev_val = prev

            # Save the current waveform in case a back-up is needed.
            prev = [has_samples, wave_str, copy(wave_data), prev_time, prev_val]

            # If the current sample occurred after the desired time window,
            # then just extend the previous sample up to the end of the window.
            if time > stop_time:
                val = prev_val  # Use the value of the previous sample.
                time = stop_time  # Extend it to the end of the window.

            # Replicate the sample's previous value up to the current time.
            wave_str += "." * (time - prev_time - 1)

            # Add the current sample's value to the waveform.

            if has_samples and (val == prev_val):
                # Just extend the previous sample if the current sample has the same value.
                wave_str += "."
            else:
                if self.num_bits > 1:
                    # Value will be shown in a data "envelope".
                    wave_str += "="
                    wave_data.append(str(val))
                else:
                    # Binary (hi/lo) waveform.
                    wave_str += str(val * 1)  # Turn value into '1' or '0'.

            has_samples = True  # The waveform now contains samples.
            prev_time = time  # Save the time and value of the
            prev_val = val  #   sample that was just added to the waveform.

        # Return a dictionary with the wave in a format that WaveDrom understands.
        wave = dict()
        wave["name"] = self.name
        wave["wave"] = wave_str
        if wave_data:
            wave["data"] = wave_data
        return wave


def _get_sample_times(*traces, **kwargs):
    """Get sample times for all the traces."""

    # Set the time boundaries for the DataFrame.
    max_stop_time = max(
        [trace.stop_time() for trace in traces if isinstance(trace, Trace)]
    )
    stop_time = kwargs.pop("stop_time", max_stop_time)
    min_start_time = min(
        [trace.start_time() for trace in traces if isinstance(trace, Trace)]
    )
    start_time = kwargs.pop("start_time", min_start_time)

    # Get all the sample times of all the traces between the start and stop times.
    times = set([start_time, stop_time])
    for trace in traces:
        times.update(
            set(trace.get_sample_times(start_time=start_time, stop_time=stop_time))
        )

    # If requested, fill in additional times between sample times.
    step = kwargs.pop("step", 0)
    if step:
        times.update(set(range(start_time, stop_time + 1, step)))

    # Sort sample times in increasing order.
    times = sorted(list(times))

    return times


def traces_to_dataframe(*traces, **kwargs):
    """
    Create Pandas dataframe of sample times and values for a set of traces.

        Args:
            *traces: A list of traces with samples. Can also contain non-Traces
                which will be ignored.

        Keywords Args:
            start_time: The earliest (left-most) time bound for the traces.
            stop_time: The latest (right-most) time bound for the traces.
            step: Set the time increment for filling in between sample times.
                If 0, then don't fill in between sample times.

        Returns:
            A Pandas dataframe of sample times and values for a set of traces.
    """

    # Extract all the traces and ignore all the non-traces.
    traces = [t for t in traces if isinstance(t, Trace)]

    # Get sample times.
    times = _get_sample_times(*traces, **kwargs)

    # Create dict of trace sample lists.
    trace_data = {tr.name: [tr.get_value(t) for t in times] for tr in traces}

    # Return a DataFrame where each column is a trace and time is the index.
    return pd.DataFrame(trace_data, index=times)


def traces_to_table_data(*traces, **kwargs):
    """
    Create table of sample times and values for a set of traces.

        Args:
            *traces: A list of traces with samples. Can also contain non-Traces
            which will be ignored.

        Keywords Args:
            start_time: The earliest (left-most) time bound for the traces.
            stop_time: The latest (right-most) time bound for the traces.
            step: Set the time increment for filling in between sample times.
                If 0, then don't fill in between sample times.

        Returns:
            Table data and a list of headers for table columns.
    """

    # Extract all the traces and ignore all the non-traces.
    traces = [t for t in traces if isinstance(t, Trace)]

    # Get sample times.
    times = _get_sample_times(*traces, **kwargs)

    # Create a table from lines of data where the first element in each row
    # is the sample time and the following elements are the trace values.
    table_data = list()
    for time in times:
        row = [trace.get_value(time) for trace in traces]
        row.insert(0, time)
        table_data.append(row)
    headers = ["Time"] + [trace.name for trace in traces]
    return table_data, headers


def traces_to_table(*traces, **kwargs):
    if "format" in kwargs:
        format = kwargs["format"]
    else:
        format = "simple"
    table_data, headers = traces_to_table_data(*traces, **kwargs)
    return tabulate(tabular_data=table_data, headers=headers, tablefmt=format)


def traces_to_text_table(*traces, **kwargs):
    if "format" not in kwargs:
        kwargs["format"] = "simple"
    print(traces_to_table(*traces, **kwargs))


def traces_to_html_table(*traces, **kwargs):
    kwargs["format"] = "html"
    tbl_html = traces_to_table(*traces, **kwargs)

    # Generate the HTML from the JSON.
    DISP.display_html(DISP.HTML(tbl_html))


def _interpolate_traces(*traces, times):
    """Interpolate trace values at times in the given list."""

    for trace in traces:
        trace.interpolate(times)


def traces_to_matplotlib(*traces, **kwargs):
    """
    Display waveforms stored in peekers in Jupyter notebook using matplotlib.
    
        Args:
            *traces: A list of traces to convert into matplotlib for display.
                Can also contain None which will create a blank trace.

        Keywords Args:
            start_time: The earliest (left-most) time bound for the waveform display.
            stop_time: The latest (right-most) time bound for the waveform display.
            title: String containing the title placed across the top of the display.
            caption: String containing the title placed across the bottom of the display.
            tick: If true, times are shown at the tick marks of the display.
            tock: If true, times are shown between the tick marks of the display.
            width: The width of the waveform display in inches.
            height: The height of the waveform display in inches.

        Returns:
            Nothing.
    """

    num_traces = len(traces)
    trace_hgt = 0.5  # Default trace height in inches.
    cycle_wid = 0.5  # Default unit cycle width in inches.

    # Handle keyword args explicitly for Python 2 compatibility.
    tock = kwargs.get("tock", False)
    tick = kwargs.get("tick", False)
    caption = kwargs.get("caption", "")
    title = kwargs.get("title", "")
    start_time = kwargs.get(
        "start_time",
        min([trace.start_time() for trace in traces if isinstance(trace, Trace)]),
    )
    stop_time = kwargs.get(
        "stop_time",
        max([trace.stop_time() for trace in traces if isinstance(trace, Trace)]),
    )
    width = kwargs.get("width", (stop_time - start_time) * cycle_wid)
    height = kwargs.get("height", num_traces * trace_hgt)

    # Create separate plot traces for each selected waveform.
    trace_hgt_pctg = 1.0 / num_traces
    fig, axes = plt.subplots(
        nrows=num_traces,
        sharex=True,
        squeeze=False,
        subplot_kw=None,
        gridspec_kw=None,
        figsize=(width, height),
    )
    axes = axes[:, 0]  # Collapse 2D matrix of subplots into a 1D list.

    # Set the caption on the X-axis label on the bottom-most trace.
    axes[-1].set_xlabel(caption)

    # Set the title for the collection of traces on the top-most trace.
    axes[0].set_title(title)

    # Set X-axis ticks at the bottom of the stack of traces.
    start = math.floor(start_time)
    stop = math.ceil(stop_time)
    axes[-1].tick_params(axis="x", length=0, which="both")  # No tick marks.
    # Set positions of tick marks so grid lines will work.
    axes[-1].set_xticks(range(start, stop + 1), minor=False)
    axes[-1].set_xticks([x + 0.5 for x in range(start, stop)], minor=True)
    # Place cycle times at tick marks or between them.
    if not tick:
        axes[-1].set_xticklabels([], minor=False)
    if tock:
        axes[-1].set_xticklabels([str(x) for x in range(start, stop)], minor=True)

    # Plot each trace waveform.
    for i, (trace, axis) in enumerate(zip(traces, axes), 1):

        # Set position of trace within stacked traces.
        axis.set_position([0.1, (num_traces - i) * trace_hgt_pctg, 0.8, trace_hgt_pctg])

        # Place grid on X axis.
        axis.grid(axis="x", color="orange", alpha=1.0)

        if not trace:
            # Leave a blank space for non-traces.
            # Remove ticks from Y axis.
            axis.set_yticks([])
            axis.tick_params(axis="y", length=0, which="both")

            # Remove the box around the subplot.
            axis.spines["left"].set_visible(False)
            axis.spines["right"].set_visible(False)
            axis.spines["top"].set_visible(False)
            axis.spines["bottom"].set_visible(False)
        else:
            trace.to_matplotlib(axis, start_time, stop_time)


def wavejson_to_wavedrom(wavejson, width=None, skin="default"):
    """
    Create WaveDrom display from WaveJSON data.

    This code is from https://github.com/witchard/ipython-wavedrom.

    Inputs:
      width: Width of the display window in pixels. If left as None, the entire
             waveform will be squashed into the width of the page. To prevent
             this, set width to a large value. The display will then become scrollable.
      skin:  Selects the set of graphic elements used to draw the waveforms.
             Allowable values are 'default' and 'narrow'.
    """

    # Set the width of the waveform display.
    style = ""
    if width != None:
        style = ' style="width: {w}px"'.format(w=str(int(width)))

    # Generate the HTML from the JSON.
    htmldata = '<div{style}><script type="WaveDrom">{json}</script></div>'.format(
        style=style, json=json.dumps(wavejson)
    )
    DISP.display_html(DISP.HTML(htmldata))

    # Trigger the WaveDrom Javascript that creates the graphical display.
    DISP.display_javascript(
        DISP.Javascript(
            data="WaveDrom.ProcessAll();",
            lib=[
                "https://wavedrom.com/wavedrom.min.js",
                "https://wavedrom.com/skins/{skin}.js".format(skin=skin),
            ],
        )
    )

    # The following allows the display of WaveDROM in the HTML files generated by nbconvert.
    # It's disabled because it makes Github's nbconvert freak out.
    setup = """
<script src="https://wavedrom.com/skins/{skin}.js" type="text/javascript"></script>
<script src="https://wavedrom.com/wavedrom.min.js" type="text/javascript"></script>
<body onload="WaveDrom.ProcessAll()">
    """.format(
        skin=skin
    )
    # DISP.display_html(DISP.HTML(setup))


def traces_to_wavejson(*traces, **kwargs):
    """
    Convert traces into a WaveJSON data structure.

    Args:
        *traces: A list of traces to convert into WaveJSON for display.
            Can also contain None which will create a blank trace.

    Keywords Args:
        start_time: The earliest (left-most) time bound for the waveform display.
        stop_time: The latest (right-most) time bound for the waveform display.
        title: String containing the title placed across the top of the display.
        caption: String containing the title placed across the bottom of the display.
        tick: If true, times are shown at the tick marks of the display.
        tock: If true, times are shown between the tick marks of the display.

    Returns:
        A dictionary with the JSON data for the waveforms.
    """

    # Handle keyword args explicitly for Python 2 compatibility.
    tock = kwargs.get("tock", False)
    tick = kwargs.get("tick", False)
    caption = kwargs.get("caption")
    title = kwargs.get("title")
    stop_time = kwargs.get(
        "stop_time",
        max([trace.stop_time() for trace in traces if isinstance(trace, Trace)]),
    )
    start_time = kwargs.get(
        "start_time",
        min([trace.start_time() for trace in traces if isinstance(trace, Trace)]),
    )

    wavejson = dict()
    wavejson["signal"] = list()
    for trace in traces:
        if isinstance(trace, Trace):
            wavejson["signal"].append(trace.to_wavejson(start_time, stop_time))
        else:
            # Insert an empty dictionary to create a blank line.
            wavejson["signal"].append(dict())

    # Create a header for the set of waveforms.
    if title or tick or tock:
        head = dict()
        if title:
            head["text"] = [
                "tspan",
                [
                    "tspan",
                    {"fill": "blue", "font-size": "16", "font-weight": "bold"},
                    title,
                ],
            ]
        if tick:
            head["tick"] = start_time
        if tock:
            head["tock"] = start_time
        wavejson["head"] = head

    # Create a footer for the set of waveforms.
    if caption or tick or tock:
        foot = dict()
        if caption:
            foot["text"] = ["tspan", ["tspan", {"font-style": "italic"}, caption]]
        if tick:
            foot["tick"] = start_time
        if tock:
            foot["tock"] = start_time
        wavejson["foot"] = foot

    return wavejson


def traces_to_wavedrom(*traces, **kwargs):
    """
    Display waveforms stored in peekers in Jupyter notebook using wavedrom.

    Args:
        *traces: A list of traces to convert into WaveJSON for display.

    Keywords Args:
        start_time: The earliest (left-most) time bound for the waveform display.
        stop_time: The latest (right-most) time bound for the waveform display.
        title: String containing the title placed across the top of the display.
        caption: String containing the title placed across the bottom of the display.
        tick: If true, times are shown at the tick marks of the display.
        tock: If true, times are shown between the tick marks of the display.
        width: The width of the waveform display in pixels.

    Returns:
        Nothing.
    """

    wavejson_to_wavedrom(
        traces_to_wavejson(*traces, **kwargs),
        width=kwargs.get("width"),
        skin=kwargs.get("skin", "default"),
    )
