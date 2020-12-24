# -*- coding: utf-8 -*-

# Copyright (c) 2017-2020, XESS Corp. The MIT License (MIT).

from __future__ import absolute_import, division, print_function, unicode_literals

import functools
from builtins import dict, int, str, super

from future import standard_library
from myhdl import EnumItemType, SignalType, always_comb, now
from myhdl._compat import integer_types
from myhdl.conversion import _toVerilog, _toVHDL

from ..peekerbase import *

standard_library.install_aliases()


class Peeker(PeekerBase):
    def __init__(self, signal, name):

        if _toVerilog._converting or _toVHDL._converting:
            # Don't create a peeker when converting to VHDL or Verilog.
            pass

        else:

            # Check to see if a signal is being monitored.
            if not isinstance(signal, SignalType):
                raise Exception(
                    "Can't add Peeker {name} to a non-Signal!".format(name=name)
                )

            super().__init__(signal, name)

            # Create combinational module that triggers when signal changes.
            @always_comb
            def peeker_logic():
                # Store signal value and sim timestamp.
                self.trace.store_sample(signal.val, now())

            # Instantiate the peeker module.
            self.instance = peeker_logic

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

    @classmethod
    def instances(cls):
        """Return a list of all the instantiated Peeker modules."""
        return [p.instance for p in cls.peekers.values()]
