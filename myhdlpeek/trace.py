# -*- coding: utf-8 -*-

# Copyright (c) 2017-2020, XESS Corp. The MIT License (MIT).

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import math
import operator
from builtins import dict, int, str, super
from collections import Counter, namedtuple
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

    unit_time = 1  # Time interval for a single tick-mark span.

    # Default matplotlib settings for a Trace.
    #     line_fmt (string): [marker][line][color] https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.pyplot.plot.html
    #     line2D (dict): https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D
    #     name_fmt (dict): https://matplotlib.org/3.2.1/api/text_api.html#matplotlib.text.Text
    #     data_fmt (dict): https://matplotlib.org/3.2.1/api/text_api.html#matplotlib.text.Text
    line_fmt = "-C0"  # solid, blue line.
    name_fmt = {}
    data_fmt = {}

    slope = 0.20  # trace transition slope as % of unit_time.

    trace_fields = ["line_fmt", "name_fmt", "data_fmt", "slope"]

    def __init__(self, *args, **kwargs):
        self.config(**kwargs)
        super().__init__(*args)
        self.name = None
        self.num_bits = 0

    @classmethod
    def config_defaults(cls, **kwargs):
        """
        Set default configuration for all Traces.

        Keyword Args:
            line_fmt (string): [marker][line][color] https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.pyplot.plot.html
            line2D (dict): https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D
            name_fmt (dict): https://matplotlib.org/3.2.1/api/text_api.html#matplotlib.text.Text
            data_fmt (dict): https://matplotlib.org/3.2.1/api/text_api.html#matplotlib.text.Text
        """
        for k, v in kwargs.items():
            if k not in cls.trace_fields:
                continue
            setattr(cls, k, copy(v))

        for k in cls.trace_fields:
            kwargs.pop(k, None)  # Remove the keyword arg.

    def config(self, **kwargs):
        """
        Set configuration for a particular Trace.

        Keyword Args:
            line_fmt (string): [marker][line][color] https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.pyplot.plot.html
            line2D (dict): https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D
            name_fmt (dict): https://matplotlib.org/3.2.1/api/text_api.html#matplotlib.text.Text
            data_fmt (dict): https://matplotlib.org/3.2.1/api/text_api.html#matplotlib.text.Text
        """
        for k, v in kwargs.items():
            if k not in self.trace_fields:
                continue
            if isinstance(v, dict):
                setattr(self, k, copy(getattr(self, k, {})))
                try:
                    getattr(self, k).update(v)
                except AttributeError:
                    setattr(self, k, {})
                    getattr(self, k).update(v)
            else:
                setattr(self, k, copy(v))
        for k in self.trace_fields:
            kwargs.pop(k, None)  # Remove the keyword arg.

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

    def get_disp_value(self, time, **kwargs):
        """Get the displayed trace value at an arbitrary time."""

        # Get the function for displaying the trace's value, first from kwargs or else from trace data_fmt attr.
        data_fmt = kwargs.get("data_fmt", getattr(self, "data_fmt"))
        repr = data_fmt.get("repr", str)

        val = self.get_value(time)
        try:
            return repr(val)
        except (TypeError, ValueError):
            return str(val)

    def get_sample_times(self, **kwargs):
        """Return list of times at which the trace was sampled."""
        start_time = kwargs.pop("start_time", self.start_time())
        stop_time = kwargs.pop("stop_time", self.stop_time())
        return [
            sample.time for sample in self if start_time <= sample.time <= stop_time
        ]

    def delay(self, delta):
        """Return the trace data shifted in time by delta units."""
        delayed_trace = copy(self)
        delayed_trace.clear()
        delayed_trace.extend([Sample(t + delta, v) for t, v in self])
        return delayed_trace

    def extend_duration(self, start_time, end_time):
        """Extend the duration of a trace."""
        # Extend the trace data to start_time unless the trace data already precedes that.
        if start_time < self[0].time:
            self.insert(0, Sample(start_time, self[0].value))
        # Extend the trace data to end_time unless the trace data already exceeds that.
        if end_time > self[-1].time:
            self.append(Sample(end_time, self[-1].value))

    def collapse_time_repeats(self):
        """Return trace with samples having the same sampling time collapsed into a single sample."""
        trace = copy(self)
        trace.clear()

        # Build the trace backwards, moving from the newest to the oldest sample.
        # Accept only samples having a time < the most recently accepted sample.
        trace.append(self[-1])
        for sample in self[-1::-1]:
            if sample.time < trace[0].time:
                trace.insert(0, sample)

        return trace

    def collapse_value_repeats(self):
        """Return trace with consecutive samples having the same value collapsed into a single sample."""
        trace = copy(self)
        trace.clear()

        # Build the trace forwards, removing any samples with the same
        # value as the previous sample.
        trace.append(self[0])
        for sample in self[1:]:
            if sample.value != trace[-1].value:
                trace.append(sample)

        return trace

    def interpolate(self, times):
        """Insert interpolated values at the times in the given list."""
        for time in times:
            insert_sample(Sample(self.get_value(time), time))

    def add_rise_fall(self, delta):
        """Add rise/fall time to trace transitions. Remove repeats before calling!"""
        trace = copy(self)
        prev_sample = trace[0]
        for sample in trace[1:]:
            # TODO: This causes a problem if sample.time - delta < prev_sample.time.
            trace.insert_sample(Sample(sample.time - delta, prev_sample.value))
            prev_sample = sample
        return trace

    def add_slope(self):
        """Return a trace with slope added to trace transitions."""
        slope = max(self.slope, 0.0001) * self.unit_time  # Don't let slope go to 0.
        return self.add_rise_fall(slope).delay(slope / 2)

    def binarize(self):
        """Return trace of sample values set to 1 (if true) or 0 (if false)."""
        return Trace([Sample(t, (v and 1) or 0) for t, v in self])

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
        return (self != self.delay(self.unit_time)).binarize()

    def posedge(self):
        return (self & (~self.delay(self.unit_time))).binarize()

    def negedge(self):
        return ((~self) & self.delay(self.unit_time)).binarize()

    def trig_times(self):
        """Return list of times trace value is true (non-zero)."""
        return [sample.time for sample in self if sample.value]

    def to_matplotlib(self, subplot, start_time, stop_time, xlim=None, **kwargs):
        """Fill a matplotlib subplot for a trace between the start & stop times."""

        # Copy trace and apply formatting to the copy.
        trace = copy(self)
        trace.config(**kwargs)

        # Set the X axis limits to clip the trace duration to the desired limits.
        if not xlim:
            xlim = (start_time, stop_time)
        subplot.set_xlim(*xlim)

        # Set the Y axis limits.
        subplot.set_ylim(-0.2, 1.2)

        # Set the Y axis label position for each trace name.
        ylbl_position = dict(
            rotation=0, horizontalalignment="right", verticalalignment="center", x=-0.01
        )
        subplot.set_ylabel(trace.name, ylbl_position, **trace.name_fmt)

        # Remove ticks from Y axis.
        subplot.set_yticks([])
        subplot.tick_params(axis="y", length=0, which="both")

        # Remove the box around the subplot.
        subplot.spines["left"].set_visible(False)
        subplot.spines["right"].set_visible(False)
        subplot.spines["top"].set_visible(False)
        subplot.spines["bottom"].set_visible(False)

        # Copy the trace while removing any consecutively-repeated values.
        trace = trace.collapse_value_repeats()

        # Insert samples for beginning/end times into a copy of the trace data.
        trace.insert_sample(Sample(start_time, self.get_value(start_time)))
        trace.insert_sample(Sample(stop_time, self.get_value(stop_time)))

        # Remove repeats of samples having the same sample time.
        trace = trace.collapse_time_repeats()

        # Extend the trace on both ends to make sure it covers the start/stop interval.
        # Count on matplotlib to clip the waveforms.
        # trace[0] = Sample(trace[0].time - self.unit_time, trace[0].value)
        # trace[-1] = Sample(trace[-1].time + self.unit_time, trace[-1].value)

        # Plot the bus or binary trace.
        if trace.num_bits > 1:
            # Multi-bit bus trace.

            # Get the function for displaying the bus value.
            repr = trace.data_fmt.get("repr", str)

            # Copy data format with repr function removed because matplotlib won't like it.
            data_fmt = copy(trace.data_fmt)
            data_fmt.pop("repr", None)

            # Get list of times the bus changes values.
            chg_times = [sample.time for sample in trace]

            # Print bus values at midpoints of the bus packets.
            time0 = chg_times[0]
            for time1 in chg_times[1:]:
                if time0 < start_time:
                    time0 = start_time
                if time1 <= time0:
                    time0 = time1
                    continue
                if time1 > stop_time:
                    time1 = stop_time
                val = trace.get_disp_value(time0, **kwargs)
                text_x = (time1 + time0) / 2
                text_y = 0.5
                subplot.text(
                    text_x,
                    text_y,
                    val,
                    horizontalalignment="center",
                    verticalalignment="center",
                    **data_fmt  # Use local data_fmt dict with repr removed.
                )
                time0 = time1
                if time0 >= stop_time:
                    break

            # Create a binary trace that toggles whenever the bus trace changes values.
            tgl_trace = copy(trace)
            tgl_trace.clear()
            value = 0
            for time in chg_times:
                tgl_trace.store_sample(value, time)
                value ^= 1

            # Slope the transitions of the toggle waveform.
            tgl_trace = tgl_trace.add_slope()

            # Create a complementary trace for drawing bus packets.
            bar_trace = tgl_trace.__not__()

            # Plot the trace packets.
            x = [sample.time for sample in tgl_trace]
            y = [sample.value for sample in tgl_trace]
            y_bar = [sample.value for sample in bar_trace]
            if isinstance(trace.line_fmt, dict):
                subplot.plot(x, y, x, y_bar, **trace.line_fmt)
            else:
                subplot.plot(x, y, trace.line_fmt, x, y_bar, trace.line_fmt)

        else:
            # Binary trace.
            trace = trace.add_slope()
            x = [sample.time for sample in trace]
            y = [sample.value for sample in trace]
            if isinstance(trace.line_fmt, dict):
                subplot.plot(x, y, **trace.line_fmt)
            else:
                subplot.plot(x, y, trace.line_fmt)

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
            wave_str += "." * (round((time - prev_time) / self.unit_time) - 1)

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


###############################################################################
# Functions for handling multiple traces follow...
###############################################################################


def calc_unit_time(*traces):
    """Calculate and return the unit time between trace samples."""
    intervals = Counter()
    for trace in traces:
        times = sorted(
            trace.collapse_time_repeats().collapse_value_repeats().get_sample_times()
        )
        intervals.update([t[1] - t[0] for t in zip(times[:-1], times[1:])])
    most_common_interval = intervals.most_common(1)[0][0]
    min_interval = min(intervals.keys())
    ratio = most_common_interval / min_interval
    if math.isclose(round(ratio), ratio, abs_tol=0.01):
        return min_interval
    raise Exception(
        "Unable to determine the unit_time for the set of Traces."
        "Manually set it using Peeker.unit_time = <simulation step time>."
    )


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
    trace_data = {
        tr.name: [tr.get_disp_value(t, **kwargs) for t in times] for tr in traces
    }

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
        row = [trace.get_disp_value(time, **kwargs) for trace in traces]
        row.insert(0, time)
        table_data.append(row)
    headers = ["Time"] + [trace.name for trace in traces]
    return table_data, headers


def traces_to_table(*traces, **kwargs):
    format = kwargs.get("format", "simple")
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
            title_fmt (dict): https://matplotlib.org/3.2.1/api/text_api.html#matplotlib.text.Text
            caption: String containing the title placed across the bottom of the display.
            caption_fmt (dict): https://matplotlib.org/3.2.1/api/text_api.html#matplotlib.text.Text
            tick: If true, times are shown at the tick marks of the display.
            tock: If true, times are shown between the tick marks of the display.
            grid_fmt (dict): https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.lines.Line2D.html#matplotlib.lines.Line2D
            time_fmt (dict): https://matplotlib.org/3.2.1/api/text_api.html#matplotlib.text.Text
            width: The width of the waveform display in inches.
            height: The height of the waveform display in inches.

        Returns:
            Figure and axes created by matplotlib.pyplot.subplots.
    """

    num_traces = len(traces)
    trace_hgt = 0.5  # Default trace height in inches.
    cycle_wid = 0.5  # Default unit cycle width in inches.

    # Handle keyword args explicitly for Python 2 compatibility.
    start_time = kwargs.pop(
        "start_time",
        min([trace.start_time() for trace in traces if isinstance(trace, Trace)]),
    )
    stop_time = kwargs.pop(
        "stop_time",
        max([trace.stop_time() for trace in traces if isinstance(trace, Trace)]),
    )
    title = kwargs.pop("title", "")
    title_fmt = {"fontweight": "bold"}
    title_fmt.update(kwargs.pop("title_fmt", {}))
    caption = kwargs.pop("caption", "")
    caption_fmt = {"fontstyle": "oblique"}
    caption_fmt.update(kwargs.pop("caption_fmt", {}))
    tick = kwargs.pop("tick", False)
    tock = kwargs.pop("tock", False)
    grid_fmt = {"color": "C1", "alpha": 1.0}
    grid_fmt.update(kwargs.pop("grid_fmt", {}))
    time_fmt = {}
    time_fmt.update(kwargs.pop("time_fmt", {}))
    width = kwargs.pop("width", (stop_time - start_time) / Trace.unit_time * cycle_wid)
    height = kwargs.pop("height", num_traces * trace_hgt)

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
    axes[-1].set_xlabel(caption, **caption_fmt)

    # Set the title for the collection of traces on the top-most trace.
    axes[0].set_title(title, **title_fmt)

    # Set X-axis ticks at the bottom of the stack of traces.
    start = math.floor(start_time / Trace.unit_time)
    stop = math.ceil(stop_time / Trace.unit_time)
    axes[-1].tick_params(axis="x", length=0, which="both")  # No tick marks.
    # Set positions of tick marks so grid lines will work.
    axes[-1].set_xticks(
        [x * Trace.unit_time for x in range(start, stop + 1)], minor=False
    )
    axes[-1].set_xticks(
        [(x + 0.5) * Trace.unit_time for x in range(start, stop)], minor=True
    )
    # Place cycle times at tick marks or between them.
    if not tick:
        axes[-1].set_xticklabels([], minor=False, **time_fmt)
    if tock:
        axes[-1].set_xticklabels(
            [str(x) for x in range(start, stop)], minor=True, **time_fmt
        )

    # Adjust the limits of the X axis so the grid doesn't get chopped-off and
    # produce artifacts if a grid line is at the right or left edge.
    bbox = axes[-1].get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    width_in_pixels = bbox.width * fig.dpi
    time_per_pixel = (stop_time - start_time) / width_in_pixels
    xlim = (start_time - time_per_pixel, stop_time + time_per_pixel)

    # Plot each trace waveform.
    for i, (trace, axis) in enumerate(zip(traces, axes), 1):

        # Set position of trace within stacked traces.
        axis.set_position([0.1, (num_traces - i) * trace_hgt_pctg, 0.8, trace_hgt_pctg])

        # Place grid on X axis.
        axis.grid(axis="x", **grid_fmt)

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
            trace.to_matplotlib(axis, start_time, stop_time, xlim, **kwargs)

    # Return figure and axes for possible further processing.
    return fig, axes


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

    # Integer start time for calculating tick/tock values.
    int_start_time = round(start_time / Trace.unit_time)

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
            head["tick"] = int_start_time
        if tock:
            head["tock"] = int_start_time
        wavejson["head"] = head

    # Create a footer for the set of waveforms.
    if caption or tick or tock:
        foot = dict()
        if caption:
            foot["text"] = ["tspan", ["tspan", {"font-style": "italic"}, caption]]
        if tick:
            foot["tick"] = int_start_time
        if tock:
            foot["tock"] = int_start_time
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
