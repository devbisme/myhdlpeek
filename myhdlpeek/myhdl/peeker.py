# -*- coding: utf-8 -*-
# Copyright (c) 2017-2024, Dave Vandenbout. The MIT License (MIT).
import functools
from builtins import dict, int, str, super
from myhdl import EnumItemType, SignalType, intbv,  always_comb, now
from myhdl.conversion import _toVerilog, _toVHDL
from ..peekerbase import *
import platform

class Peeker(PeekerBase):
    """Extends the PeekerBase to create an object that peeks or monitors a signal for use with myhdl."""

    def __init__(self, signal, name):
        """
        Instantiates a new Peeker object if not converting to VHDL or Verilog.

        Args:
            signal (mydhl SignalType): The myhdl signal to be monitored.
            name (str): The name of the Peeker object.

        Note:
            This method creates a new instance of a peeker module that triggers
            whenever the signal changes, and sets the width of the signal.
        """
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
                """Stores the value of the signal and the current simulation timestamp."""
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
                    elif isinstance(signal.val, int):
                        #represent an int by machines architecture size
                        self.trace.num_bits = int(platform.architecture()[0].split('bit')[0])
                    elif isinstance(signal.val, intbv):
                        #if intbv then use the assigned bits
                        self.trace.num_bits = signal.val._nrbits
                    else:
                        # Unknown type of value. Just give it this width and hope.
                        self.trace.num_bits = 32

    @classmethod
    def instances(cls):
        """
        Returns a list of all the instantiated Peeker modules.

        Returns:
            list: A list of all instantiated Peeker modules.
        """
        return [p.instance for p in cls.peekers.values()]
