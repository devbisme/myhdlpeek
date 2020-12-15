# -*- coding: utf-8 -*-

# Copyright (c) 2017-2020, XESS Corp. The MIT License (MIT).

from __future__ import absolute_import, division, print_function, unicode_literals

import functools
from builtins import dict, int, str, super

from future import standard_library
from myhdl import EnumItemType, SignalType, always_comb, now
from myhdl._compat import integer_types
from myhdl.conversion import _toVerilog, _toVHDL

# from .. import peekerbase
from ..peekerbase import *

standard_library.install_aliases()


class Peeker(PeekerBase):
    def __init__(self, signal, name):

        super().__init__(signal, name)

        if _toVerilog._converting or _toVHDL._converting:
            # Don't create a peeker when converting to VHDL or Verilog.
            pass

        else:
            # Check to see if a signal is being monitored.
            if not isinstance(signal, SignalType):
                raise Exception(
                    "Can't add Peeker {name} to a non-Signal!".format(name=name)
                )

            # Create storage for signal trace.
            self.trace = Trace()

            # Create combinational module that triggers when signal changes.
            @always_comb
            def peeker_logic():
                # Store signal value and sim timestamp.
                self.trace.store_sample(signal.val, now())

            # Instantiate the peeker module.
            self.instance = peeker_logic

            # Assign a unique name to this peeker.
            self.name_dup = False  # Start off assuming the name has no duplicates.
            index = 0  # Starting index for disambiguating duplicates.
            nm = "{name}[{index}]".format(
                **locals()
            )  # Create name with bracketed index.
            # Search through the peeker names for a match.
            while nm in self._peekers:
                # A match was found, so mark the matching names as duplicates.
                self._peekers[nm].name_dup = True
                self.name_dup = True
                # Go to the next index and see if that name is taken.
                index += 1
                nm = "{name}[{index}]".format(**locals())
            self.trace.name = nm  # Assign the unique name.

            # Set the width of the signal.
            if isinstance(signal.val, EnumItemType):
                # For enums, set the width to always be greater than 1 so the
                # trace displays as bus packets and not a binary waveform.
                self.trace.num_bits = max(2, signal._nrbits)
            else:
                self.trace.num_bits = signal._nrbits
                if self.trace.num_bits == 0:
                    if isinstance(signal.val, bool):
                        self.trace.num_bits = 1
                    elif isinstance(signal.val, integer_types):
                        # Gotta pick some width for integers. This sounds good.
                        self.trace.num_bits = 32
                    else:
                        # Unknown type of value. Just give it this width and hope.
                        self.trace.num_bits = 32

            # Keep a reference to the signal so we can get info about it later, if needed.
            self.signal = signal

            # Add this peeker to the global list.
            self._peekers[self.trace.name] = self
