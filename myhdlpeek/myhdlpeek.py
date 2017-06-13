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

# a dict of all peekers created, this is useful if peekers are added in
# buried levels of hierarchy.
all_peekers = {}


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
            if sample.time >= time:
                return i
        return len(self)

    def get_value(self, time):
        '''Get the trace value at an arbitrary time.'''

        # Get the index of the sample with the time >= to the given time.
        index = min( len(self)-1, self.get_index(time) )

        # If the selected sample was taken at a time after the given time,
        # then backup to the previous sample (but not past the beginning).
        if self[index].time > time:
            index = max(0, index-1)

        # Return the value of the sample at the indexed position.
        return self[index].value

    def to_wavejson(self, start_time, stop_time):
        '''Generate the WaveJSON data for a trace between the start & stop times.'''

        has_samples = False     # No samples currently on the wave.
        wave_str = ''           # No samples, so wave string is empty.
        wave_data = list()      # No samples, so wave data values are empty.
        prev_time = start_time  # Set time of previous sample to the wave starting time.
        prev_val = None         # Value of previous sample starts at non-number.

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
                val = prev_val   # Use the value of the previous sample.
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
            prev_time = time    # Save the time and value of the
            prev_val = val      #   sample that was just added to the waveform.

        # Return a dictionary with the wave in a format that WaveDrom understands.
        wave = dict()
        wave['name'] = self.name
        wave['wave'] = wave_str
        if wave_data:
            wave['data'] = wave_data
        return wave


class Peeker(object):
    def __init__(self, *args, **kwargs):
        '''
        '''
        # clear out the signal list if converting (no tracing/peeking)
        if _toVerilog._converting or _toVHDL._converting:
            signals = {}

        # @todo: if another `Peeker` was passed, merge the tsigs ...
        # walk through the *args and **kwargs and create the dict of signals,
        # if a peeker
        signals, peekers = [], []
        for sig in args:
            if isinstance(sig, SignalType):
                signals += [(sig._name, sig)]
            if isinstance(sig, Peeker):
                signals += [(nm, tsig['sig'])
                            for nm, tsig in sig.trace_signals.items()]
        for nm, sig in kwargs.items():
            if isinstance(sig, SignalType):
                signals += [(nm, sig)]
            if isinstance(sig, Peeker):
                signals += [(nm, tsig['sig'])
                            for nm, tsig in sig.trace_signals.items()]


        self.trace_signals = {}
        for nm, sig in signals:
            # Check to see if a signal is being monitored.
            if not isinstance(sig, SignalType):
                raise Exception("Can't add Peeker {name} to a non-Signal!".format(name=nm))

            # get a unique name if duplicates in the signals kwargs
            unm = self.unique_name(nm, sig)

            t = Trace()
            self.trace_signals[unm] = dict(sig=sig, trace=t)
            t.name = unm
            # Set the width of the signal.
            t.numbits = sig._nrbits
            if t.numbits == 0:
                if isinstance(sig.val, bool):
                    t.numbits = 1
                elif isinstance(sig.val, integer_types):
                    t.numbits = 32  # Gotta pick some width for integers. This sounds good.
                else:
                    t.numbits = 32  # Unknown type of value. Just give it this width and hope.

        self._instances = [self.peeker_process(tsig)
                           for nm, tsig in self.trace_signals.items()]

        # add this Peeker to the global dictionary of peekers
        if 'name' in kwargs:
            pnm = kwargs['name']
        else:
            pnm = 'peeker_{:d}'.format(len(all_peekers))
        all_peekers[pnm] = self

    def unique_name(self, nm, sig):
        # Assign a unique name to this peeker.
        unm, index = nm, 0
        # Search through the peeker names for a match.
        for snm, tsig in self.trace_signals.items():
            if unm == snm and sig is not tsig['sig'] :
                # Go to the next index and see if that name is taken.
                index += 1
                unm = '{name}[{index}]'.format(nm, self.index)
        return unm


    def peeker_process(self, signal):
        trace, sig = signal['trace'], signal['sig']
        @always_comb
        def peeker_logic():
            trace.store_sample(sig.val)

        return peeker_logic

    def clear(self):
        '''Clear the global list of Peekers.'''
        self.trace_signals = dict()

    def instances(self):
        '''Return a list of all the instantiated Peeker modules.'''
        return self._instances

    def start_time(self):
        '''Return the time of the first signal transition captured by the peekers.'''
        return min((v['trace'].start_time() for nm, v in self.trace_signals.items()))

    def stop_time(self):
        '''Return the time of the last signal transition captured by the peekers.'''
        return max((v['trace'].stop_time() for nm, v in self.trace_signals.items()))

    def to_wavejson(self, *names, start_time=0, stop_time=None, title=None,
                    caption=None, tick=False, tock=False):
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

        if stop_time is None:
            stop_time = self.stop_time()

        wavejson = dict()
        wavejson['signal'] = list()
        for nm, tsig in self.trace_signals.items():
            # if a list of names where
            if names is not None and nm not in names:
                continue
            sig, trace = tsig['sig'], tsig['trace']
            try:
                wavejson['signal'].append(trace.to_wavejson(start_time, stop_time))
            except AttributeError:
                # This happens if no peeker with the matching name is found.
                # In that case, insert an empty dictionary to create a blank line.
                wavejson['signal'].append(dict())

        # Create a header for the set of waveforms.
        if title or tick or tock:
            head = dict()
            if title:
                head['text'] = ['tspan', ['tspan', {'fill':'blue', 'font-size':'16', 'font-weight':'bold'}, title]]
            if tick:
                head['tick'] = start_time
            if tock:
                head['tock'] = start_time
            wavejson['head'] = head

        # Create a footer for the set of waveforms.
        if caption or tick or tock:
            foot = dict()
            if caption:
                foot['text'] = ['tspan', ['tspan', {'font-style': 'italic'}, caption]]
            if tick:
                foot['tick'] = start_time
            if tock:
                foot['tock'] = start_time
            wavejson['foot'] = foot

        return wavejson

    def to_wavedrom(self, start_time=0, stop_time=None, title=None,
                    caption=None, tick=False, tock=False, width=None):
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

        wavejson_to_wavedrom(self.to_wavejson(start_time=start_time, stop_time=stop_time,
            title=title, caption=caption, tick=tick, tock=tock), width=width)


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
    DISP.display_javascript(DISP.Javascript(
        data='WaveDrom.ProcessAll();',
        lib=['http://wavedrom.com/wavedrom.min.js',
             'http://wavedrom.com/skins/default.js']))

    # The following allows the display of WaveDROM in the HTML files generated by nbconvert.
    # It's disabled because it makes Github's nbconvert freak out.
    setup = '''
<script src="http://wavedrom.com/skins/default.js" type="text/javascript"></script>
<script src="http://wavedrom.com/wavedrom.min.js" type="text/javascript"></script>
<body onload="WaveDrom.ProcessAll()">
    '''
    #DISP.display_html(DISP.HTML(setup))


def sort_names(names):
    '''
    Sort peeker names by index and alphabetically.

    For example, the peeker names would be sorted as a[0], b[0], a[1], b[1], ...
    '''

    def index_key(lbl):
        '''Index sorting.'''
        m = re.match('.*\[(\d+)\]$', lbl)  # Get the bracketed index.
        if m:
            return int(m.group(1)) # Return the index as an integer.
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

def merge_all():
    ''' merge all the peekers into a single peeker '''
    return Peeker(all_peekers.values())
