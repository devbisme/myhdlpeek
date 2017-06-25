# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (C) 2017 by XESS Corp.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import super
from builtins import int
from builtins import dict
from builtins import str
from future import standard_library
standard_library.install_aliases()

import sys
import re
from collections import namedtuple
from copy import copy, deepcopy
import logging

from myhdl import Signal, always_comb, intbv, now, SignalType
from myhdl._compat import integer_types
from myhdl.conversion import _toVerilog
from myhdl.conversion import _toVHDL

from tabulate import tabulate

import IPython.display as DISP
import json

logger = logging.getLogger('myhdlpeek')

USING_PYTHON2 = (sys.version_info.major == 2)
USING_PYTHON3 = not USING_PYTHON2

DEBUG_OVERVIEW = logging.DEBUG
DEBUG_DETAILED = logging.DEBUG - 1
DEBUG_OBSESSIVE = logging.DEBUG - 2

# Waveform samples consist of a time and a value.
Sample = namedtuple('Sample', 'time value')


class Trace(list):
    '''
    Trace objects are lists that store a sequence of samples. The samples
    should be arranged in order of ascending sample time.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = None
        self.numbits = 0

    def store_sample(self, value):
        '''Store a value and the current time into the trace.'''
        self.append(Sample(now(), copy(value)))

    def insert_sample(self, sample):
        '''Insert a sample into the correct position within a trace'''
        index = self.get_index(sample.time)
        self.insert(index, sample)

    def start_time(self):
        '''Return the time of the first sample in the trace.'''
        return self[0][0]

    def stop_time(self):
        '''Return the time of the last sample in the trace.'''
        return self[-1][0]

    def get_index(self, time):
        '''Return the position to insert a sample with the given time.'''

        for i, sample in enumerate(self):
            # Return the index of the 1st sample with a time GREATER than the
            # given time because the sample will be inserted BEFORE that index.
            if sample.time > time:
                return i

        # Didn't find a sample with a time greater than the given time, so
        # the insertion point is the end of the trace list.
        return len(self)

    def get_value(self, time):
        '''Get the trace value at an arbitrary time.'''

        # Return the signal value immediately BEFORE the insertion index.
        return self[max(0, self.get_index(time)-1)].value

    def get_sample_times(self):
        '''Return list of times at which the trace was sampled.'''
        return [sample.time for sample in self]

    def to_wavejson(self, start_time, stop_time):
        '''Generate the WaveJSON data for a trace between the start & stop times.'''

        has_samples = False  # No samples currently on the wave.
        wave_str = ''  # No samples, so wave string is empty.
        wave_data = list()  # No samples, so wave data values are empty.
        prev_time = start_time  # Set time of previous sample to the wave starting time.
        prev_val = None  # Value of previous sample starts at non-number.

        # Save the current state of the waveform.
        prev = [has_samples, wave_str, copy(wave_data), prev_time, prev_val]

        # Insert samples into a copy of the waveform data. These samples bound
        # the beginning and ending times of the waveform.
        bounded_samples = copy(self)
        bounded_samples.insert_sample(
            Sample(start_time, self.get_value(start_time)))
        bounded_samples.insert_sample(
            Sample(stop_time, self.get_value(stop_time)))

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
            prev = [
                has_samples, wave_str,
                copy(wave_data), prev_time, prev_val
            ]

            # If the current sample occurred after the desired time window,
            # then just extend the previous sample up to the end of the window.
            if time > stop_time:
                val = prev_val  # Use the value of the previous sample.
                time = stop_time  # Extend it to the end of the window.

            # Replicate the sample's previous value up to the current time.
            wave_str += '.' * (time - prev_time - 1)

            # Add the current sample's value to the waveform.
            if val == prev_val and has_samples:
                # Just extend the previous sample if the current sample has the same value.
                wave_str += '.'
            else:
                # Otherwise, add a new sample value.
                if self.numbits > 1:
                    # Value will be shown in a data "envelope".
                    wave_str += '='
                    wave_data.append(str(val))
                else:
                    # Binary (hi/lo) waveform.
                    wave_str += str(val * 1)  # Turn value into '1' or '0'.

            has_samples = True  # The waveform now contains samples.
            prev_time = time  # Save the time and value of the
            prev_val = val  #   sample that was just added to the waveform.

        # Return a dictionary with the wave in a format that WaveDrom understands.
        wave = dict()
        wave['name'] = self.name
        wave['wave'] = wave_str
        if wave_data:
            wave['data'] = wave_data
        return wave


class Peeker(object):
    _peekers = dict()  # Global list of all Peekers.

    def __init__(self, signal, name):

        if _toVerilog._converting or _toVHDL._converting:
            # Don't create a peeker when converting to VHDL or Verilog.
            pass

        else:
            # Check to see if a signal is being monitored.
            if not isinstance(signal, SignalType):
                raise Exception("Can't add Peeker {name} to a non-Signal!".
                                format(name=name))

            # Create storage for signal trace.
            self.trace = Trace()

            # Create combinational module that triggers when signal changes.
            @always_comb
            def peeker_logic():
                self.trace.store_sample(
                    signal.val)  # Store signal value and sim timestamp.

            # Instantiate the peeker module.
            self.instance = peeker_logic

            # Assign a unique name to this peeker.
            self.name_dup = False  # Start off assuming the name has no duplicates.
            index = 0  # Starting index for disambiguating duplicates.
            nm = '{name}[{index}]'.format(
                **locals())  # Create name with bracketed index.
            # Search through the peeker names for a match.
            while nm in self._peekers:
                # A match was found, so mark the matching names as duplicates.
                self._peekers[nm].name_dup = True
                self.name_dup = True
                # Go to the next index and see if that name is taken.
                index += 1
                nm = '{name}[{index}]'.format(**locals())
            self.trace.name = nm  # Assign the unique name.

            # Set the width of the signal.
            self.trace.numbits = signal._nrbits
            if self.trace.numbits == 0:
                if isinstance(signal.val, bool):
                    self.trace.numbits = 1
                elif isinstance(signal.val, integer_types):
                    self.trace.numbits = 32  # Gotta pick some width for integers. This sounds good.
                else:
                    self.trace.numbits = 32  # Unknown type of value. Just give it this width and hope.

            # Keep a reference to the signal so we can get info about it later, if needed.
            self.signal = signal

            # Add this peeker to the global list.
            self._peekers[self.trace.name] = self

    @classmethod
    def clear(cls):
        '''Clear the global list of Peekers.'''
        cls._peekers = dict()

    @classmethod
    def instances(cls):
        '''Return a list of all the instantiated Peeker modules.'''
        return (p.instance for p in cls.peekers())

    @classmethod
    def peekers(cls):
        '''Return a list of all the Peekers.'''
        return cls._peekers.values()

    @classmethod
    def start_time(cls):
        '''Return the time of the first signal transition captured by the peekers.'''
        return min((p.trace.start_time() for p in cls.peekers()))

    @classmethod
    def stop_time(cls):
        '''Return the time of the last signal transition captured by the peekers.'''
        return max((p.trace.stop_time() for p in cls.peekers()))

    @classmethod
    def _clean_names(cls):
        '''
        Remove indices from non-repeated peeker names that don't need them.

        When created, all peekers get an index appended to their name to
        disambiguate any repeated names. If the name isn't actually repeated,
        then the index is removed.
        '''

        index_re = '\[\d+\]$'
        for name, peeker in cls._peekers.items():
            if not peeker.name_dup:
                new_name = re.sub(index_re, '', name)
                if new_name != name:
                    peeker.trace.name = new_name
                    cls._peekers[new_name] = cls._peekers.pop(name)

    @classmethod
    def to_wavejson(cls, *names, **kwargs):
        '''
        Convert waveforms stored in peekers into a WaveJSON data structure.

        Args:
            *names: A list of strings containing the names for the Peekers that
                will be displayed. A string may contain multiple,
                space-separated names.

        Keywords Args:
            start_time: The earliest (left-most) time bound for the waveform display.
            stop_time: The latest (right-most) time bound for the waveform display.
            title: String containing the title placed across the top of the display.
            caption: String containing the title placed across the bottom of the display.
            tick: If true, times are shown at the tick marks of the display.
            tock: If true, times are shown between the tick marks of the display.

        Returns:
            A dictionary with the JSON data for the waveforms.
        '''

        # Handle keyword args explicitly for Python 2 compatibility.
        if 'tock' in kwargs:
            tock = kwargs['tock']
        else:
            tock = False
        if 'tick' in kwargs:
            tick = kwargs['tick']
        else:
            tick = False
        if 'caption' in kwargs:
            caption = kwargs['caption']
        else:
            caption = None
        if 'title' in kwargs:
            title = kwargs['title']
        else:
            title = None
        if 'stop_time' in kwargs:
            stop_time = kwargs['stop_time']
        else:
            stop_time = cls.stop_time()
        if 'start_time' in kwargs:
            start_time = kwargs['start_time']
        else:
            start_time = cls.start_time()

        cls._clean_names()

        if names:
            # Go through the provided names and split any containing spaces
            # into individual names.
            names = [nm for name in names for nm in name.split()]
        else:
            # If no names provided, use all the peekers.
            names = _sort_names(cls._peekers.keys())

        # Collect all the Peekers matching the names.
        peekers = [cls._peekers.get(name) for name in names]

        if stop_time is None:
            stop_time = cls.stop_time()

        wavejson = dict()
        wavejson['signal'] = list()
        for p in peekers:
            try:
                wavejson['signal'].append(
                    p.trace.to_wavejson(start_time, stop_time))
            except AttributeError:
                # This happens if no peeker with the matching name is found.
                # In that case, insert an empty dictionary to create a blank line.
                wavejson['signal'].append(dict())

        # Create a header for the set of waveforms.
        if title or tick or tock:
            head = dict()
            if title:
                head['text'] = [
                    'tspan', [
                        'tspan', {
                            'fill': 'blue',
                            'font-size': '16',
                            'font-weight': 'bold'
                        }, title
                    ]
                ]
            if tick:
                head['tick'] = start_time
            if tock:
                head['tock'] = start_time
            wavejson['head'] = head

        # Create a footer for the set of waveforms.
        if caption or tick or tock:
            foot = dict()
            if caption:
                foot['text'] = [
                    'tspan', ['tspan', {
                        'font-style': 'italic'
                    }, caption]
                ]
            if tick:
                foot['tick'] = start_time
            if tock:
                foot['tock'] = start_time
            wavejson['foot'] = foot

        return wavejson

    @classmethod
    def to_wavedrom(cls, *names, **kwargs):
        '''
        Display waveforms stored in peekers in Jupyter notebook.

        Args:
            *names: A list of strings containing the names for the Peekers that
                will be displayed. A string may contain multiple,
                space-separated names.

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
        '''

        # Handle keyword args explicitly for Python 2 compatibility.
        if 'width' in kwargs:
            width = kwargs['width']
            del kwargs['width']
        else:
            width = None

        wavejson_to_wavedrom(cls.to_wavejson(*names, **kwargs), width=width)

    @classmethod
    def to_table_data(cls, *names, **kwargs):
        '''
        Convert traces stored in peekers into a list of times and trace values.

        Args:
            *names: A list of strings containing the names for the Peekers that
                will be processed. A string may contain multiple,
                space-separated names.

        Keywords Args:
            start_time: The earliest (left-most) time bound for the traces.
            stop_time: The latest (right-most) time bound for the traces.

        Returns:
            List of lists containing the time and the value of each trace at that time.
        '''

        if 'caption' in kwargs:
            caption = kwargs['caption']
        else:
            caption = None
        if 'title' in kwargs:
            title = kwargs['title']
        else:
            title = None
        if 'stop_time' in kwargs:
            stop_time = kwargs['stop_time']
        else:
            stop_time = cls.stop_time()
        if 'start_time' in kwargs:
            start_time = kwargs['start_time']
        else:
            start_time = cls.start_time()

        cls._clean_names()

        if names:
            # Go through the provided names and split any containing spaces
            # into individual names.
            names = [nm for name in names for nm in name.split()]
        else:
            # If no names provided, use all the peekers.
            names = _sort_names(cls._peekers.keys())

        # Collect all the Peekers matching the names.
        peekers = [cls._peekers.get(name) for name in names]

        # Get all the sample times of all the traces.
        times = set()
        for peeker in peekers:
            times.update(set(peeker.trace.get_sample_times()))
        times = sorted(list(times))

        # Create a table from lines of data where the first element in each line
        # is the sample time and the following elements are the trace values.
        table_data = list()
        for time in times:
            if start_time <= time <= stop_time:
                line_data = [p.trace.get_value(time) for p in peekers]
                line_data.insert(0, time)
                table_data.append(line_data)
        headers = ['Time'] + names
        return table_data, headers

    @classmethod
    def to_table(cls, *names, **kwargs):

        if 'format' in kwargs:
            format = kwargs['format']
        else:
            format = 'simple'

        table_data, headers = cls.to_table_data(*names, **kwargs)
        return tabulate(tabular_data=table_data, headers=headers, tablefmt=format)

    @classmethod
    def show_text_table(cls, *names, **kwargs):
        if 'format' not in kwargs:
            kwargs['format'] = 'simple'
        print(cls.to_table(*names, **kwargs))

    @classmethod
    def show_html_table(cls, *names, **kwargs):
        kwargs['format'] = 'html'
        tbl_html = cls.to_table(*names, **kwargs)

        # Generate the HTML from the JSON.
        DISP.display_html(DISP.HTML(tbl_html))
        

show_waveforms = Peeker.to_wavedrom
show_text_table = Peeker.show_text_table
show_html_table = Peeker.show_html_table


def wavejson_to_wavedrom(wavejson, width=None):
    '''
    Create WaveDrom display from WaveJSON data.

    This code is from https://github.com/witchard/ipython-wavedrom.
    '''

    # Set the width of the waveform display.
    style = ''
    if width != None:
        style = ' style="width: {w}px"'.format(w=str(int(width)))

    # Generate the HTML from the JSON.
    htmldata = '<div{style}><script type="WaveDrom">{json}</script></div>'.format(
        style=style, json=json.dumps(wavejson))
    DISP.display_html(DISP.HTML(htmldata))

    # Trigger the WaveDrom Javascript that creates the graphical display.
    DISP.display_javascript(
        DISP.Javascript(
            data='WaveDrom.ProcessAll();',
            lib=[
                'http://wavedrom.com/wavedrom.min.js',
                'http://wavedrom.com/skins/default.js'
            ]))

    # The following allows the display of WaveDROM in the HTML files generated by nbconvert.
    # It's disabled because it makes Github's nbconvert freak out.
    setup = '''
<script src="http://wavedrom.com/skins/default.js" type="text/javascript"></script>
<script src="http://wavedrom.com/wavedrom.min.js" type="text/javascript"></script>
<body onload="WaveDrom.ProcessAll()">
    '''
    #DISP.display_html(DISP.HTML(setup))


def _sort_names(names):
    '''
    Sort peeker names by index and alphabetically.

    For example, the peeker names would be sorted as a[0], b[0], a[1], b[1], ...
    '''

    def index_key(lbl):
        '''Index sorting.'''
        m = re.match('.*\[(\d+)\]$', lbl)  # Get the bracketed index.
        if m:
            return int(m.group(1))  # Return the index as an integer.
        return -1  # No index found so it comes before everything else.

    def name_key(lbl):
        '''Name sorting.'''
        m = re.match('^([^\[]+)', lbl)  # Get name preceding bracketed index.
        if m:
            return m.group(1)  # Return name.
        return ''  # No name found.

    srt_names = sorted(names, key=name_key)
    srt_names = sorted(srt_names, key=index_key)
    return srt_names
